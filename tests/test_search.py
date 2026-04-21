"""Tests for localization key/text search."""

import pytest

from devtools_mcp.localization.scripts.check_existing_translations import (
    search_by_key,
    search_by_text,
)


def _make_strings(entries: dict) -> dict:
    """Build xcstrings-style strings dict."""
    result = {}
    for key, vals in entries.items():
        localizations = {}
        if "en" in vals:
            localizations["en"] = {
                "stringUnit": {"state": "translated", "value": vals["en"]}
            }
        if "ar" in vals:
            localizations["ar"] = {
                "stringUnit": {"state": "translated", "value": vals["ar"]}
            }
        result[key] = {"localizations": localizations}
    return result


class TestSearchByKey:
    """Tests for search_by_key()."""

    def test_exact_match(self):
        strings = _make_strings({"account.number": {"en": "Account Number"}})
        results = search_by_key(strings, "account.number")
        assert len(results) == 1
        assert results[0]["key"] == "account.number"

    def test_partial_match(self):
        strings = _make_strings({
            "account.number": {"en": "Account Number"},
            "account.name": {"en": "Account Name"},
            "profile.email": {"en": "Email"},
        })
        results = search_by_key(strings, "account")
        assert len(results) == 2

    def test_case_insensitive(self):
        strings = _make_strings({"Account Number": {"en": "Account Number"}})
        results = search_by_key(strings, "account number")
        assert len(results) == 1

    def test_dots_and_spaces_normalized(self):
        """Dots and spaces are stripped for matching."""
        strings = _make_strings({"account.number": {"en": "Account Number"}})
        results = search_by_key(strings, "Account Number")
        assert len(results) == 1

    def test_no_match(self):
        strings = _make_strings({"account.number": {"en": "Account Number"}})
        results = search_by_key(strings, "zzz.nothing")
        assert len(results) == 0


class TestSearchByText:
    """Tests for search_by_text()."""

    def test_finds_by_english_text(self):
        strings = _make_strings({
            "submit": {"en": "Submit"},
            "cancel": {"en": "Cancel"},
        })
        results = search_by_text(strings, "Submit")
        assert len(results) == 1
        assert results[0]["key"] == "submit"

    def test_case_insensitive(self):
        strings = _make_strings({"submit": {"en": "Submit Form"}})
        results = search_by_text(strings, "submit form")
        assert len(results) == 1

    def test_partial_text_match(self):
        strings = _make_strings({
            "submit.form": {"en": "Submit Form"},
            "submit.button": {"en": "Submit"},
        })
        results = search_by_text(strings, "Submit")
        assert len(results) == 2

    def test_no_match(self):
        strings = _make_strings({"submit": {"en": "Submit"}})
        results = search_by_text(strings, "Nonexistent")
        assert len(results) == 0
