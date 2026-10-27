"""The seam between "understanding a message" and "searching the database".

The assistant works in two independent steps:

    message --(QueryParser)--> ParsedQuery --(chat_service)--> SearchCriteria --(PropertyRepository)--> SQL

Today the only parser is the deterministic, rule-based one in ``nlp_parser.py`` (free, offline, testable).
An optional AI/LLM parser can be added later WITHOUT touching the search code: write a class with a ``name`` and a
``parse(message, known_localities) -> ParsedQuery`` method, then return an instance from
``configured_primary_parser()`` when its credentials are present in the environment. Rules that keep it safe:

  * the LLM must only produce structured criteria (a ``ParsedQuery``); listings always come from the database;
  * if no credentials are configured, ``configured_primary_parser()`` returns ``None`` and nothing else changes;
  * if the optional parser raises for any reason, the rule-based parser answers instead (see ``parse_message``).
"""
import logging
from typing import Protocol

from app.services.nlp_parser import ParsedQuery, parse_query

logger = logging.getLogger("realestate")

LocalityIndex = dict[str, tuple[str, str]]


class QueryParser(Protocol):
    name: str

    def parse(self, message: str, known_localities: LocalityIndex | None = None) -> ParsedQuery: ...


class RuleBasedParser:
    """Deterministic parser: regular expressions + vocabulary. This is NOT a large language model."""

    name = "rule-based"

    def parse(self, message: str, known_localities: LocalityIndex | None = None) -> ParsedQuery:
        return parse_query(message, known_localities)


RULE_BASED = RuleBasedParser()


def configured_primary_parser() -> QueryParser | None:
    """Extension point for an optional AI parser. Returns None because no AI provider is wired in (by design)."""
    return None


def parse_message(message: str, known_localities: LocalityIndex | None = None,
                  primary: QueryParser | None = None) -> tuple[ParsedQuery, str]:
    """Parse with the optional ``primary`` parser when given, falling back to the rule-based one on any failure.

    Returns ``(parsed_query, parser_name)`` so the API can state honestly which parser produced the criteria.
    """
    if primary is not None:
        try:
            return primary.parse(message, known_localities), primary.name
        except Exception:  # noqa: BLE001 - an optional component must never break core search
            logger.warning("Optional parser %r failed; using the rule-based parser instead", primary.name, exc_info=True)
    return RULE_BASED.parse(message, known_localities), RULE_BASED.name
