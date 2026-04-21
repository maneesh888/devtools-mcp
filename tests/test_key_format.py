"""Tests for localization key format validation and conversion."""

import pytest

from devtools_mcp.localization.xcstrings import validate_key_format, to_new_format, is_old_format


class TestValidateKeyFormat:
    """Tests for validate_key_format()."""

    def test_valid_simple_key(self):
        valid, err = validate_key_format("account.number")
        assert valid is True
        assert err == ""

    def test_valid_single_word(self):
        valid, err = validate_key_format("submit")
        assert valid is True

    def test_valid_with_numbers(self):
        valid, err = validate_key_format("step.1.of.3")
        assert valid is True

    def test_valid_deep_nesting(self):
        valid, err = validate_key_format("profile.settings.email.label")
        assert valid is True

    def test_rejects_empty(self):
        valid, err = validate_key_format("")
        assert valid is False
        assert "empty" in err.lower()

    def test_rejects_uppercase(self):
        valid, err = validate_key_format("Account.Number")
        assert valid is False
        assert "lowercase" in err.lower()

    def test_rejects_spaces(self):
        valid, err = validate_key_format("account number")
        assert valid is False
        assert "spaces" in err.lower()

    def test_rejects_hyphens(self):
        valid, err = validate_key_format("account-number")
        assert valid is False
        assert "a-z" in err.lower()

    def test_rejects_underscores(self):
        valid, err = validate_key_format("account_number")
        assert valid is False

    def test_rejects_leading_dot(self):
        valid, err = validate_key_format(".account.number")
        assert valid is False
        assert "dot" in err.lower()

    def test_rejects_trailing_dot(self):
        valid, err = validate_key_format("account.number.")
        assert valid is False
        assert "dot" in err.lower()


class TestIsOldFormat:
    """Tests for is_old_format()."""

    def test_uppercase_is_old(self):
        assert is_old_format("Select Nationality") is True

    def test_single_capital_is_old(self):
        assert is_old_format("Remove") is True

    def test_camelcase_is_old(self):
        assert is_old_format("AccountNumber") is True

    def test_lowercase_is_new(self):
        assert is_old_format("select.nationality") is False

    def test_single_lowercase_is_new(self):
        assert is_old_format("remove") is False

    def test_empty_string(self):
        assert is_old_format("") is False


class TestToNewFormat:
    """Tests for to_new_format()."""

    def test_spaces_to_dots(self):
        assert to_new_format("Select Nationality") == "select.nationality"

    def test_single_word(self):
        assert to_new_format("Remove") == "remove"

    def test_already_lowercase(self):
        assert to_new_format("remove") == "remove"

    def test_mixed_case_with_spaces(self):
        assert to_new_format("Step 1 of 3") == "step.1.of.3"

    def test_camelcase_no_spaces(self):
        # Note: CamelCase without spaces just gets lowercased, no dot splitting
        assert to_new_format("AccountNumber") == "accountnumber"
