"""The optional-AI seam: a failing or absent AI parser must never break search."""
from decimal import Decimal

from app.services.nlp_parser import ParsedQuery
from app.services.query_understanding import configured_primary_parser, parse_message


class _FakeAIParser:
    name = "fake-ai"

    def parse(self, message, known_localities=None):
        return ParsedQuery(city="Pune", max_price=Decimal(1_000_000), listing_type="buy")


class _BrokenAIParser:
    name = "broken-ai"

    def parse(self, message, known_localities=None):
        raise RuntimeError("provider timeout")


def test_no_ai_provider_is_configured_by_default():
    assert configured_primary_parser() is None


def test_rule_based_parser_is_used_without_an_ai_parser():
    parsed, name = parse_message("2BHK apartment in Hyderabad under 60 lakh")
    assert name == "rule-based" and parsed.city == "Hyderabad" and parsed.max_price == Decimal(6_000_000)


def test_optional_parser_is_used_and_labelled_when_it_works():
    parsed, name = parse_message("anything", primary=_FakeAIParser())
    assert name == "fake-ai" and parsed.city == "Pune"


def test_failing_optional_parser_falls_back_to_rules():
    parsed, name = parse_message("2BHK apartment in Hyderabad under 60 lakh", primary=_BrokenAIParser())
    assert name == "rule-based" and parsed.city == "Hyderabad"
