"""Composite pre-commit audit for iOS projects.

Dispatches across multiple check categories (localization, design system,
file metadata, Swift hygiene) and returns a unified report. Designed to
be invoked as a single MCP tool so natural-language "run a pre-commit
audit" requests reliably trigger the audit instead of the agent improvising
with Read/Grep.
"""

from .core import audit_changed_files, get_changed_files, resolve_paths

__all__ = ["audit_changed_files", "get_changed_files", "resolve_paths"]
