"""Settings validation (runs without touching any real .env file)."""
import re

import pytest
from pydantic import ValidationError

from app.core.config import DEV_CORS_ORIGIN_REGEX, Settings

BASE = {"database_url": "mysql+pymysql://user:pw@localhost:3306/db?charset=utf8mb4", "secret_key": "x" * 40}


def make(**overrides) -> Settings:
    return Settings(_env_file=None, **{**BASE, **overrides})


def test_development_allows_any_localhost_port_production_does_not():
    assert make(environment="development").effective_cors_origin_regex == DEV_CORS_ORIGIN_REGEX
    assert make(environment="production").effective_cors_origin_regex is None


def test_explicit_regex_is_used_and_blank_means_default():
    assert make(environment="production", cors_origin_regex=r"^https://app\.example\.com$").effective_cors_origin_regex
    assert make(environment="production", cors_origin_regex="   ").effective_cors_origin_regex is None


def test_production_refuses_allow_everything_regex():
    with pytest.raises(ValidationError):
        make(environment="production", cors_origin_regex=".*")


@pytest.mark.parametrize("origin,allowed", [
    ("http://localhost:5174", True), ("https://127.0.0.1:8080", True), ("http://[::1]:5173", True), ("http://localhost", True),
    ("http://localhost.evil.com", False), ("http://localhost:5174.evil.com", False), ("https://evil.com", False),
    ("http://evil.com/?http://localhost", False)])
def test_dev_regex_matches_only_real_localhost_origins(origin, allowed):
    assert bool(re.fullmatch(DEV_CORS_ORIGIN_REGEX, origin)) is allowed


def test_origin_list_is_trimmed_and_has_no_trailing_slash():
    s = make(cors_origins=" http://localhost:5173/ , https://app.example.com ,")
    assert s.cors_origin_list == ["http://localhost:5173", "https://app.example.com"]


def test_bare_mysql_url_is_upgraded_to_pymysql():
    assert make(database_url="mysql://u:p@localhost/db").database_url.startswith("mysql+pymysql://")


@pytest.mark.parametrize("url", ["postgresql://u:p@localhost/db", "mysql+pymysql://u:CHANGE_ME@localhost/db", "not a url"])
def test_bad_database_urls_are_rejected(url):
    with pytest.raises(ValidationError):
        make(database_url=url)


def test_production_requires_a_strong_secret():
    with pytest.raises(ValidationError):
        make(environment="production", secret_key="short")
    with pytest.raises(ValidationError):
        make(environment="production", secret_key="CHANGE_ME_" + "x" * 40)
    assert make(environment="production", secret_key="k" * 48).is_production
