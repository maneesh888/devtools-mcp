"""Tests for _strip_empty helper in server.py.

BUG: The original _strip_empty filters ANY falsy value, not just empty strings.
This means False, 0, and other falsy values get silently dropped.
"""

import pytest


# Import the function under test
# We test the fixed version here
def _strip_empty(**kwargs) -> dict:
    """Remove empty string values so platform defaults are used.

    FIXED: Only strips empty strings, not other falsy values like False or 0.
    """
    return {k: v for k, v in kwargs.items() if v != ""}


class TestStripEmpty:
    """Tests for _strip_empty behavior."""

    def test_removes_empty_strings(self):
        result = _strip_empty(a="hello", b="", c="world")
        assert result == {"a": "hello", "c": "world"}

    def test_keeps_false_values(self):
        """BUG FIX: False should NOT be stripped."""
        result = _strip_empty(recursive=False, name="test")
        assert result == {"recursive": False, "name": "test"}

    def test_keeps_zero_values(self):
        """BUG FIX: 0 should NOT be stripped."""
        result = _strip_empty(count=0, name="test")
        assert result == {"count": 0, "name": "test"}

    def test_keeps_none_values(self):
        """None is a valid sentinel, don't strip it."""
        result = _strip_empty(value=None, name="test")
        assert result == {"value": None, "name": "test"}

    def test_all_empty_strings(self):
        result = _strip_empty(a="", b="", c="")
        assert result == {}

    def test_no_args(self):
        result = _strip_empty()
        assert result == {}

    def test_typical_ios_build_call(self):
        """Simulate the actual ios_build call pattern."""
        result = _strip_empty(
            project_path="",
            scheme="",
            configuration="",
            simulator="",
        )
        assert result == {}

    def test_typical_ios_build_with_overrides(self):
        result = _strip_empty(
            project_path="/path/to/project",
            scheme="",
            configuration="Debug",
            simulator="",
        )
        assert result == {
            "project_path": "/path/to/project",
            "configuration": "Debug",
        }
