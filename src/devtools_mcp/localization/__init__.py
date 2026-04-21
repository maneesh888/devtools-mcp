"""Localization module for DevTools MCP Server.

Provides xcstrings file operations (check, search, add, remove),
migration execution, and key usage search.
"""

from .auditor import find_key_usage
from .migrator import (
    execute_migration,
    remove_old_key,
)
from .xcstrings import (
    LocalizationEntry,
    XCStringsFile,
    add_key,
    add_keys_bulk,
    check_key,
    copy_arabic_translation,
    read_xcstrings,
    remove_key,
    search_keys,
    validate_key_format,
    to_new_format,
)

__all__ = [
    # xcstrings
    "LocalizationEntry",
    "XCStringsFile",
    "add_key",
    "add_keys_bulk",
    "check_key",
    "copy_arabic_translation",
    "read_xcstrings",
    "remove_key",
    "search_keys",
    "validate_key_format",
    "to_new_format",
    # auditor
    "find_key_usage",
    # migrator
    "execute_migration",
    "remove_old_key",
]
