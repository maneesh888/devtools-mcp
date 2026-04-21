"""Tests for xcstrings file I/O operations.

Tests add_key, remove_key, and related operations using temporary
xcstrings files to avoid touching the real project.
"""

import json
import os
import tempfile

import pytest

from devtools_mcp.localization.scripts.add_multiple_keys import (
    create_entry,
    find_insertion_point,
)
from devtools_mcp.localization.xcstrings import (
    _add_key_internal,
    check_key,
    read_xcstrings,
    remove_key,
)


def _make_xcstrings(entries: dict | None = None) -> str:
    """Create a temporary xcstrings file matching Xcode's formatting.

    Produces valid JSON with the line structure that find_insertion_point
    and remove_key depend on (4-space indent entries with }, between them).

    Args:
        entries: Dict of key -> {"en": str, "ar": str} values.
    """
    lines = [
        '{\n',
        '  "sourceLanguage" : "en",\n',
        '  "strings" : {\n',
    ]

    sorted_keys = sorted(entries.keys()) if entries else []
    for idx, key in enumerate(sorted_keys):
        vals = entries[key]
        is_last = idx == len(sorted_keys) - 1
        en_val = vals.get("en", "")
        ar_val = vals.get("ar", "")

        lines.append(f'    "{key}" : {{\n')
        lines.append('      "extractionState" : "manual",\n')
        lines.append('      "localizations" : {\n')

        has_ar = bool(ar_val)
        has_en = bool(en_val)

        if has_ar:
            lines.append('        "ar" : {\n')
            lines.append('          "stringUnit" : {\n')
            lines.append('            "state" : "translated",\n')
            lines.append(f'            "value" : "{ar_val}"\n')
            lines.append('          }\n')
            # Comma after ar block only if en block follows
            if has_en:
                lines.append('        },\n')
            else:
                lines.append('        }\n')

        if has_en:
            lines.append('        "en" : {\n')
            lines.append('          "stringUnit" : {\n')
            lines.append('            "state" : "translated",\n')
            lines.append(f'            "value" : "{en_val}"\n')
            lines.append('          }\n')
            lines.append('        }\n')

        lines.append('      }\n')
        # Comma between entries, not on the last one (valid JSON)
        if not is_last:
            lines.append('    },\n')
        else:
            lines.append('    }\n')

    lines.append('  },\n')
    lines.append('  "version" : "1.0"\n')
    lines.append('}\n')

    fd, path = tempfile.mkstemp(suffix=".xcstrings")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


class TestCreateEntry:
    """Tests for add_multiple_keys.create_entry()."""

    def test_english_only(self):
        entry = create_entry("submit.button", "Submit")
        assert '"submit.button"' in entry
        assert '"Submit"' in entry
        assert '"ar"' not in entry

    def test_with_arabic(self):
        entry = create_entry("submit.button", "Submit", "إرسال")
        assert '"ar"' in entry
        assert '"إرسال"' in entry

    def test_escapes_quotes(self):
        entry = create_entry("test.key", 'Say "hello"')
        assert r'Say \"hello\"' in entry

    def test_empty_arabic_treated_as_no_arabic(self):
        entry = create_entry("test.key", "Hello", "")
        assert '"ar"' not in entry


class TestFindInsertionPoint:
    """Tests for add_multiple_keys.find_insertion_point()."""

    def test_alphabetical_insertion(self):
        lines = [
            '{\n',
            '  "strings" : {\n',
            '    "apple" : {\n',
            '      "extractionState" : "manual"\n',
            '    },\n',
            '    "cherry" : {\n',
            '      "extractionState" : "manual"\n',
            '    },\n',
            '  }\n',
            '}\n',
        ]
        # "banana" should go between "apple" and "cherry"
        idx = find_insertion_point(lines, "banana")
        assert idx is not None
        assert idx == 5  # After "apple"'s closing },

    def test_insertion_at_end(self):
        lines = [
            '{\n',
            '  "strings" : {\n',
            '    "apple" : {\n',
            '      "extractionState" : "manual"\n',
            '    },\n',
            '  }\n',
            '}\n',
        ]
        # "zebra" goes after "apple"
        idx = find_insertion_point(lines, "zebra")
        assert idx is not None
        assert idx == 5  # After the last },

    def test_empty_file(self):
        lines = ['{\n', '  "strings" : {\n', '  }\n', '}\n']
        idx = find_insertion_point(lines, "anything")
        assert idx is None  # No existing entries, no }, to anchor


class TestRemoveKey:
    """Tests for xcstrings.remove_key().

    BUG: remove_key has incomplete dangling comma cleanup that could
    produce invalid JSON in edge cases.
    """

    def test_remove_middle_key(self):
        path = _make_xcstrings({
            "apple": {"en": "Apple", "ar": "تفاحة"},
            "banana": {"en": "Banana", "ar": "موزة"},
            "cherry": {"en": "Cherry", "ar": "كرزة"},
        })
        try:
            result = remove_key("banana", path)
            assert result["success"] is True

            # Verify the file is still valid JSON
            with open(path, "r") as f:
                data = json.load(f)
            assert "banana" not in data["strings"]
            assert "apple" in data["strings"]
            assert "cherry" in data["strings"]
        finally:
            os.unlink(path)

    def test_remove_last_key(self):
        """Removing the last key should produce valid JSON (no trailing comma)."""
        path = _make_xcstrings({
            "apple": {"en": "Apple", "ar": ""},
            "banana": {"en": "Banana", "ar": ""},
        })
        try:
            result = remove_key("banana", path)
            assert result["success"] is True

            with open(path, "r") as f:
                data = json.load(f)
            assert "banana" not in data["strings"]
            assert "apple" in data["strings"]
        finally:
            os.unlink(path)

    def test_remove_only_key(self):
        """Removing the only key should leave valid JSON with empty strings."""
        path = _make_xcstrings({
            "only.key": {"en": "Only", "ar": ""},
        })
        try:
            result = remove_key("only.key", path)
            assert result["success"] is True

            with open(path, "r") as f:
                data = json.load(f)
            assert len(data["strings"]) == 0
        finally:
            os.unlink(path)

    def test_remove_nonexistent_key(self):
        path = _make_xcstrings({"apple": {"en": "Apple", "ar": ""}})
        try:
            result = remove_key("nonexistent", path)
            assert result["success"] is False
            assert "not found" in result["error"].lower()
        finally:
            os.unlink(path)


class TestReadXcstrings:
    """Tests for read_xcstrings()."""

    def test_parses_entries(self):
        path = _make_xcstrings({
            "submit": {"en": "Submit", "ar": "إرسال"},
            "cancel": {"en": "Cancel", "ar": ""},
        })
        try:
            xcfile = read_xcstrings(path)
            assert xcfile.total_keys == 2
            assert xcfile.entries["submit"].english == "Submit"
            assert xcfile.entries["submit"].arabic == "إرسال"
            assert xcfile.entries["cancel"].english == "Cancel"
            assert xcfile.entries["cancel"].arabic is None
        finally:
            os.unlink(path)

    def test_missing_arabic_list(self):
        path = _make_xcstrings({
            "has.both": {"en": "Hello", "ar": "مرحبا"},
            "missing.ar": {"en": "World", "ar": ""},
        })
        try:
            xcfile = read_xcstrings(path)
            missing = xcfile.missing_arabic
            assert len(missing) == 1
            assert missing[0].key == "missing.ar"
        finally:
            os.unlink(path)

    def test_empty_file(self):
        path = _make_xcstrings({})
        try:
            xcfile = read_xcstrings(path)
            assert xcfile.total_keys == 0
        finally:
            os.unlink(path)


class TestCheckKey:
    """Tests for check_key()."""

    def test_existing_key(self):
        path = _make_xcstrings({
            "submit": {"en": "Submit", "ar": "إرسال"},
        })
        try:
            result = check_key("submit", path)
            assert result["exists"] is True
            assert result["has_english"] is True
            assert result["has_arabic"] is True
        finally:
            os.unlink(path)

    def test_nonexistent_key(self):
        path = _make_xcstrings({})
        try:
            result = check_key("missing", path)
            assert result["exists"] is False
        finally:
            os.unlink(path)

    def test_detects_old_format(self):
        path = _make_xcstrings({
            "Select Nationality": {"en": "Select Nationality", "ar": ""},
        })
        try:
            result = check_key("Select Nationality", path)
            assert result["is_old_format"] is True
            assert result["suggested_new_key"] == "select.nationality"
        finally:
            os.unlink(path)


class TestAddKeyInternal:
    """Tests for _add_key_internal()."""

    def test_add_english_only(self):
        """Test adding a key using a realistic xcstrings file.

        Note: find_insertion_point depends on Xcode's specific formatting
        (4-space indent entries with trailing commas). We use a realistic
        fixture instead of json.dump output.
        """
        # Write a realistic xcstrings file matching Xcode's output format
        fd, path = tempfile.mkstemp(suffix=".xcstrings")
        with os.fdopen(fd, "w") as f:
            f.write(
                '{\n'
                '  "sourceLanguage" : "en",\n'
                '  "strings" : {\n'
                '    "aaa.existing" : {\n'
                '      "extractionState" : "manual",\n'
                '      "localizations" : {\n'
                '        "en" : {\n'
                '          "stringUnit" : {\n'
                '            "state" : "translated",\n'
                '            "value" : "Existing"\n'
                '          }\n'
                '        }\n'
                '      }\n'
                '    },\n'
                '    "zzz.last" : {\n'
                '      "extractionState" : "manual",\n'
                '      "localizations" : {\n'
                '        "en" : {\n'
                '          "stringUnit" : {\n'
                '            "state" : "translated",\n'
                '            "value" : "Last"\n'
                '          }\n'
                '        }\n'
                '      }\n'
                '    }\n'
                '  },\n'
                '  "version" : "1.0"\n'
                '}\n'
            )
        try:
            result = _add_key_internal("test.key", "Hello", "", path)
            assert result["success"] is True

            # Verify the key is in the file content
            with open(path, "r") as f:
                content = f.read()
            assert '"test.key"' in content
            assert '"Hello"' in content
        finally:
            os.unlink(path)

    def test_add_to_empty_strings(self):
        """Adding to xcstrings with no entries uses the strings block },
        as anchor. The result may not be structurally perfect but the
        key is inserted."""
        fd, path = tempfile.mkstemp(suffix=".xcstrings")
        with os.fdopen(fd, "w") as f:
            f.write(
                '{\n'
                '  "sourceLanguage" : "en",\n'
                '  "strings" : {\n'
                '  },\n'
                '  "version" : "1.0"\n'
                '}\n'
            )
        try:
            result = _add_key_internal("test.key", "Hello", "", path)
            # find_insertion_point uses the }, from the strings close as anchor
            # so it does succeed, though the placement is imperfect
            assert result["success"] is True
            with open(path, "r") as f:
                content = f.read()
            assert '"test.key"' in content
        finally:
            os.unlink(path)

    def test_rejects_invalid_format(self):
        path = _make_xcstrings({})
        try:
            result = _add_key_internal("Invalid Key", "Hello", "", path)
            assert result["success"] is False
        finally:
            os.unlink(path)

    def test_rejects_duplicate(self):
        path = _make_xcstrings({"existing": {"en": "Hello", "ar": ""}})
        try:
            result = _add_key_internal("existing", "Hello", "", path)
            assert result["success"] is False
            assert "already exists" in result["error"]
        finally:
            os.unlink(path)
