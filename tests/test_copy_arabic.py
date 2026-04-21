"""Tests for Arabic translation copy logic."""

import pytest

from devtools_mcp.localization.scripts.copy_arabic_translations import copy_arabic


def _make_data(entries: dict) -> dict:
    """Build xcstrings-style data dict for testing."""
    strings = {}
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
        strings[key] = {"localizations": localizations}
    return {"strings": strings}


class TestCopyArabic:
    """Tests for copy_arabic_translations.copy_arabic()."""

    def test_copies_arabic_successfully(self):
        data = _make_data({
            "old.key": {"en": "Hello", "ar": "مرحبا"},
            "new.key": {"en": "Hello"},
        })
        success, value = copy_arabic(data, "new.key", "old.key")
        assert success is True
        assert value == "مرحبا"

        # Verify in-memory mutation happened
        new_ar = (
            data["strings"]["new.key"]["localizations"]["ar"]["stringUnit"]["value"]
        )
        assert new_ar == "مرحبا"

    def test_fails_source_not_found(self):
        data = _make_data({"new.key": {"en": "Hello"}})
        success, msg = copy_arabic(data, "new.key", "nonexistent")
        assert success is False
        assert "not found" in msg.lower()

    def test_fails_target_not_found(self):
        data = _make_data({"old.key": {"en": "Hello", "ar": "مرحبا"}})
        success, msg = copy_arabic(data, "nonexistent", "old.key")
        assert success is False
        assert "not found" in msg.lower()

    def test_fails_source_no_arabic(self):
        data = _make_data({
            "old.key": {"en": "Hello"},
            "new.key": {"en": "Hello"},
        })
        success, msg = copy_arabic(data, "new.key", "old.key")
        assert success is False
        assert "no arabic" in msg.lower()

    def test_overwrites_existing_arabic(self):
        data = _make_data({
            "source": {"en": "Hello", "ar": "مرحبا"},
            "target": {"en": "Hello", "ar": "قديم"},
        })
        success, value = copy_arabic(data, "target", "source")
        assert success is True
        assert value == "مرحبا"
        new_ar = data["strings"]["target"]["localizations"]["ar"]["stringUnit"]["value"]
        assert new_ar == "مرحبا"
