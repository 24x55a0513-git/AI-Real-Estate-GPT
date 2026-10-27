"""Real Estate GPT assistant: parser -> structured criteria -> real database search -> explained results.

Nothing here invents listings: every property returned comes from the database query, and every 'reason' is
computed from the property's actual stored values.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession, Property, User
from app.repositories.property_repository import PropertyRepository
from app.schemas.chat import ChatRequest, ChatResponse, PropertyMatch, SearchCriteria, Suggestion
from app.schemas.property import PropertyFilters, PropertyOut
from app.services.formatting import format_inr
from app.services.nlp_parser import ParsedQuery
from app.services.query_understanding import configured_primary_parser, parse_message

MAX_RESULTS = 6
MAX_COMPARE = 4

HELP_TEXT = (
    "Hi! I'm the Real Estate GPT assistant. I understand property requests written in plain English and search "
    "the demo listings in our database. I use rule-based language parsing (not a large language model), so "
    "simple, specific requests work best. Try:\n"
    "• Find a 2BHK apartment in Hyderabad under ₹60 lakh with parking\n"
    "• Show villas in Bengaluru between ₹80 lakh and ₹1.5 crore\n"
    "• Find a rental flat in Hyderabad under ₹25,000 per month\n"
    "• Compare the cheapest matching properties")

UNCLEAR_TEXT = (
    "I couldn't pick out any search requirements from that. Tell me a city (Hyderabad, Bengaluru, Chennai or "
    "Pune), whether you want to buy or rent, and any budget, bedrooms or property type. For example: "
    "“2BHK apartment in Pune under ₹70 lakh”.")


class SessionNotFound(Exception):
    pass


# ------------------------------------------------------------------ conversions
def criteria_from_parsed(pq: ParsedQuery) -> SearchCriteria:
    return SearchCriteria(
        city=pq.city, locality=pq.locality, listing_type=pq.listing_type, property_types=pq.property_types,
        min_price=pq.min_price, max_price=pq.max_price, min_bedrooms=pq.min_bedrooms, max_bedrooms=pq.max_bedrooms,
        min_bathrooms=pq.min_bathrooms, min_area=pq.min_area, max_area=pq.max_area, has_parking=pq.has_parking,
        furnishing=pq.furnishing, amenities=pq.amenities, sort=pq.sort)


def criteria_to_filters(c: SearchCriteria, page_size: int = MAX_RESULTS) -> PropertyFilters:
    return PropertyFilters(
        city=c.city, locality=c.locality, listing_type=c.listing_type, property_types=c.property_types,
        min_price=c.min_price, max_price=c.max_price, min_bedrooms=c.min_bedrooms, max_bedrooms=c.max_bedrooms,
        min_bathrooms=c.min_bathrooms, min_area=c.min_area, max_area=c.max_area, has_parking=c.has_parking,
        furnishing=c.furnishing, amenities=c.amenities, sort=c.sort or "price_asc", page_size=page_size)


def merge_criteria(context: SearchCriteria, new: SearchCriteria) -> SearchCriteria:
    """Refine the previous search with a follow-up message: new non-empty values win."""
    merged = context.model_copy(deep=True)
    for name in SearchCriteria.model_fields:
        value = getattr(new, name)
        if value not in (None, [], False):
            setattr(merged, name, value)
    if new.min_price is not None or new.max_price is not None:  # a fresh budget replaces the old one
        merged.min_price, merged.max_price = new.min_price, new.max_price
    return merged


def summarize(c: SearchCriteria) -> str:
    parts: list[str] = []
    if c.listing_type:
        parts.append("rent" if c.listing_type.value == "rent" else "buy")
    if c.property_types:
        parts.append("/".join(t.value.replace("_", " ") for t in c.property_types))
    if c.min_bedrooms is not None or c.max_bedrooms is not None:
        if c.min_bedrooms is not None and c.min_bedrooms == c.max_bedrooms:
            parts.append(f"{c.min_bedrooms} bedroom")
        elif c.min_bedrooms is not None and c.max_bedrooms is not None:
            parts.append(f"{c.min_bedrooms}-{c.max_bedrooms} bedrooms")
        elif c.min_bedrooms is not None:
            parts.append(f"{c.min_bedrooms}+ bedrooms")
        else:
            parts.append(f"up to {c.max_bedrooms} bedrooms")
    if c.min_bathrooms:
        parts.append(f"{c.min_bathrooms}+ bathrooms")
    place = ", ".join(x for x in (c.locality, c.city) if x)
    if place:
        parts.append(f"in {place}")
    lt = c.listing_type.value if c.listing_type else None
    if c.min_price is not None and c.max_price is not None:
        parts.append(f"{format_inr(c.min_price, lt)} to {format_inr(c.max_price, lt)}")
    elif c.max_price is not None:
        parts.append(f"up to {format_inr(c.max_price, lt)}")
    elif c.min_price is not None:
        parts.append(f"from {format_inr(c.min_price, lt)}")
    if c.min_area and c.max_area:
        parts.append(f"{c.min_area:,}-{c.max_area:,} sq ft")
    elif c.min_area:
        parts.append(f"at least {c.min_area:,} sq ft")
    elif c.max_area:
        parts.append(f"up to {c.max_area:,} sq ft")
    if c.furnishing:
        parts.append(c.furnishing.value.replace("_", " "))
    if c.has_parking:
        parts.append("with parking")
    if c.amenities:
        parts.append("with " + ", ".join(c.amenities))
    return " · ".join(parts) if parts else "all listings"


def explain_match(p: Property, c: SearchCriteria) -> list[str]:
    """Reasons derived strictly from the stored property values and the criteria that were applied."""
    r: list[str] = []
    lt = p.listing_type
    if c.locality:
        r.append(f"Located in {p.locality}, {p.city}")
    elif c.city:
        r.append(f"Located in {p.city} ({p.locality})")
    if c.listing_type:
        r.append("Listed for rent" if lt == "rent" else "Listed for sale")
    if c.property_types:
        r.append(f"Property type: {p.property_type.replace('_', ' ')}")
    price = format_inr(p.price, lt)
    if c.max_price is not None and c.min_price is not None:
        r.append(f"Price {price} is within your range")
    elif c.max_price is not None:
        r.append(f"Price {price} is within your budget of {format_inr(c.max_price, lt)}")
    elif c.min_price is not None:
        r.append(f"Price {price} is at or above {format_inr(c.min_price, lt)}")
    if c.min_bedrooms is not None or c.max_bedrooms is not None:
        r.append(f"{p.bedrooms} bedroom{'s' if p.bedrooms != 1 else ''}")
    if c.min_bathrooms:
        r.append(f"{p.bathrooms} bathrooms")
    if c.min_area or c.max_area:
        r.append(f"{p.area_sqft:,} sq ft")
    if c.has_parking and p.has_parking:
        r.append("Parking available")
    if c.furnishing and p.furnishing:
        r.append(f"Furnishing: {p.furnishing.replace('_', ' ')}")
    have = {a.lower(): a for a in p.amenities}
    for want in c.amenities:
        if want.lower() in have:
            r.append(f"Has {have[want.lower()]}")
    return r or ["Active demo listing"]


# ------------------------------------------------------------------ relaxation suggestions
def _relaxations(c: SearchCriteria) -> list[tuple[str, SearchCriteria]]:
    out: list[tuple[str, SearchCriteria]] = []

    def add(label: str, **changes):
        out.append((label, c.model_copy(update=changes, deep=True)))

    if c.has_parking or c.amenities:
        add("Drop parking/amenity requirements", has_parking=None, amenities=[])
    if c.furnishing:
        add("Drop the furnishing preference", furnishing=None)
    if c.max_price is not None:
        add("Increase the maximum budget by 20%", max_price=Decimal(c.max_price) * Decimal("1.2"))
        add("Remove the maximum budget", max_price=None)
    if c.min_bedrooms is not None or c.max_bedrooms is not None:
        add("Allow any number of bedrooms", min_bedrooms=None, max_bedrooms=None)
    if c.min_area or c.max_area:
        add("Remove the area requirement", min_area=None, max_area=None)
    if c.property_types:
        add("Include all property types", property_types=[])
    if c.locality:
        add(f"Search all of {c.city or 'the city'} instead of just {c.locality}", locality=None)
    return out


# ------------------------------------------------------------------ orchestration
def _get_session(db: Session, user: User, session_id: int | None, first_message: str) -> ChatSession:
    if session_id is not None:
        sess = db.scalars(select(ChatSession).where(ChatSession.id == session_id,
                                                    ChatSession.user_id == user.id)).first()
        if not sess:
            raise SessionNotFound  # also covers other users' sessions: no information leak
        return sess
    sess = ChatSession(user_id=user.id, title=first_message.strip()[:100] or "New chat")
    db.add(sess)
    db.flush()
    return sess


def handle_message(db: Session, user: User | None, req: ChatRequest) -> ChatResponse:
    repo = PropertyRepository(db)
    response = _respond(repo, req)
    if user is not None:  # anonymous visitors get answers, but nothing is stored
        sess = _get_session(db, user, req.session_id, req.message)
        db.add(ChatMessage(session_id=sess.id, role="user", content=req.message))
        db.add(ChatMessage(session_id=sess.id, role="assistant", content=response.reply,
                           criteria=response.criteria.model_dump(mode="json"),
                           property_ids=[m.property.id for m in response.matches]))
        sess.title = sess.title or req.message[:100]
        db.commit()
        response.session_id = sess.id
    return response


def _respond(repo: PropertyRepository, req: ChatRequest) -> ChatResponse:
    empty = SearchCriteria()
    parser_name = "rule-based"  # replaced below with whichever parser actually handled the message

    def reply_only(intent: str, text: str, criteria: SearchCriteria = empty, **kw) -> ChatResponse:
        return ChatResponse(session_id=None, intent=intent, reply=text, criteria=criteria, matches=[],
                            total_matches=0, parser=parser_name, **kw)

    # ---- 1. understand (or take explicit criteria from a clicked suggestion)
    if req.criteria_override is not None:
        criteria, intent, assumptions, warnings = req.criteria_override, "search", [], []
    else:
        parsed, parser_name = parse_message(req.message, repo.locality_index(), configured_primary_parser())
        intent, assumptions, warnings = parsed.intent, parsed.assumptions, parsed.warnings
        new = criteria_from_parsed(parsed)
        criteria = new
        ctx = req.context_criteria
        if ctx is not None and not (parsed.city or parsed.locality):
            if parsed.has_criteria():  # follow-up refinement of the previous search
                criteria = merge_criteria(ctx, new)
                if intent in ("unclear", "greeting"):
                    intent = "search"
            elif intent == "compare":
                criteria = ctx.model_copy(update={"sort": new.sort or ctx.sort}, deep=True)
        if intent == "greeting":
            return reply_only("greeting", HELP_TEXT)
        if intent == "unclear":
            return reply_only("unclear", UNCLEAR_TEXT, criteria=ctx or empty)
        if intent == "compare" and not parsed.has_criteria() and ctx is None:
            return reply_only("compare", "Tell me what to search for first (for example “2BHK in Pune under ₹70 "
                              "lakh”), then ask me to compare the cheapest matches.")
        if parsed.listing_type is None and any("buy or rent" in w for w in warnings):
            return reply_only("clarify", "Do you want to buy or to rent? Tell me which and I'll search.",
                              criteria=criteria, warnings=warnings, assumptions=assumptions)

    # ---- 2. unsupported city -> be honest
    facets = repo.facets()
    if criteria.city and criteria.city.lower() not in {c.lower() for c in facets["cities"]}:
        cities = ", ".join(facets["cities"]) or "none yet"
        return reply_only("search", f"The demo database has no listings in {criteria.city}. "
                          f"Available cities: {cities}.", criteria=criteria, warnings=warnings, assumptions=assumptions)

    # ---- 3. query the real database
    if intent == "compare":
        criteria = criteria.model_copy(update={"sort": criteria.sort or "price_asc"})
    filters = criteria_to_filters(criteria, page_size=MAX_COMPARE if intent == "compare" else MAX_RESULTS)
    props, total = repo.search(filters)
    matches = [PropertyMatch(property=PropertyOut.model_validate(p), reasons=explain_match(p, criteria)) for p in props]
    summary = summarize(criteria)

    # ---- 4. compose an honest reply
    suggestions: list[Suggestion] = []
    compare_ids: list[int] = []
    if total == 0:
        for label, relaxed in _relaxations(criteria):
            n = repo.count(criteria_to_filters(relaxed))
            if n > 0:
                suggestions.append(Suggestion(label=label, criteria=relaxed, match_count=n))
            if len(suggestions) == 3:
                break
        reply = f"I couldn't find any matching demo properties for: {summary}."
        reply += (" Here are some adjustments that would return results." if suggestions
                  else " Try a different city, a wider budget, or fewer requirements.")
    elif intent == "compare":
        compare_ids = [m.property.id for m in matches]
        if len(compare_ids) < 2:
            reply = f"Only {total} demo property matches ({summary}), so there is nothing to compare yet."
            compare_ids = []
        else:
            reply = (f"Comparing the {len(compare_ids)} lowest-priced matches for: {summary}. "
                     "Open the comparison table for the full side-by-side view.")
    else:
        shown = f"Showing {len(matches)}." if total > len(matches) else ""
        reply = (f"I found {total} matching demo {'property' if total == 1 else 'properties'} for: {summary}. "
                 f"{shown}").strip()
    if any("looks like" in w for w in warnings):
        reply += " Please check the note below: your amount may not match buy/rent."

    return ChatResponse(session_id=None, intent=intent, reply=reply, criteria=criteria, matches=matches,
                        total_matches=total, suggestions=suggestions, assumptions=assumptions, warnings=warnings,
                        compare_ids=compare_ids, parser=parser_name)
