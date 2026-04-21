"""Localization audit — missing Arabic, missing keys, hardcoded strings,
old-format key usage.

Delegates per-key lookup to xcstrings.check_key to stay in sync with
the rest of the MCP.
"""

from __future__ import annotations

import os
import re

from ..localization.xcstrings import check_key, is_old_format

# &&"key" usage in Swift (primary pattern used by String+Localization.swift)
_SWIFT_LOC_KEY_RE = re.compile(r'&&"([^"]+)"')

# NSLocalizedString usage in Objective-C
_OBJC_LOC_KEY_RE = re.compile(r'NSLocalizedString\(\s*@"([^"]+)"')

# Hardcoded user-facing string candidates — matches quoted strings starting
# with an uppercase ASCII letter followed by letters/spaces. Leading `&`
# excludes the localization operator. Tuned to match the auditor guideline.
_SWIFT_HARDCODED_RE = re.compile(r'(?<!&)"([A-Z][a-zA-Z\s]{2,})"')

# Noise filters — reject strings that look like identifiers, file paths,
# SF Symbol names, or internal constants rather than user-facing copy.
_IDENT_HINTS = (
    ".", "/", "_", "-", "://", "system:", "SF",
)
_SF_SYMBOL_SUFFIXES = (".fill", ".circle", ".slash")

# Debug / logging call patterns — any hardcoded string on these lines is
# considered diagnostic output, not user-facing copy.
_DEBUG_CONTEXT_RE = re.compile(
    r"\b(?:print|debugPrint|dump|NSLog|os_log|assert|assertionFailure|"
    r"precondition|preconditionFailure|fatalError)\s*\("
)


def audit_localization(
    file_path: str,
    content: str,
    xcstrings_path: str = "",
) -> list[dict]:
    """Return localization issues for the given file content."""
    issues: list[dict] = []
    is_swift = file_path.endswith(".swift")

    key_re = _SWIFT_LOC_KEY_RE if is_swift else _OBJC_LOC_KEY_RE

    seen_keys: set[str] = set()
    for line_no, line in _iter_code_lines(content):
        for match in key_re.finditer(line):
            key = match.group(1)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            status = check_key(key, xcstrings_path)

            if not status.get("exists"):
                issues.append({
                    "category": "localization",
                    "code": "LOC001",
                    "severity": "error",
                    "line": line_no,
                    "message": f"Key '{key}' not found in Localizable.xcstrings",
                    "suggested_fix": f"Add '{key}' via localization_add_key",
                })
                continue

            if not status.get("has_english"):
                issues.append({
                    "category": "localization",
                    "code": "LOC002",
                    "severity": "error",
                    "line": line_no,
                    "message": f"Key '{key}' exists but English value is empty",
                    "suggested_fix": f"Add English value for '{key}'",
                })

            if not status.get("has_arabic") and not is_old_format(key):
                issues.append({
                    "category": "localization",
                    "code": "LOC003",
                    "severity": "warning",
                    "line": line_no,
                    "message": f"Key '{key}' missing Arabic translation",
                    "suggested_fix": "Send key to marketing for Arabic translation",
                })

            if is_old_format(key):
                new_key = status.get("suggested_new_key") or ""
                issues.append({
                    "category": "localization",
                    "code": "LOC004",
                    "severity": "warning",
                    "line": line_no,
                    "message": (
                        f"Old-format key '{key}' in use"
                        + (f"; new key '{new_key}' is preferred" if new_key else "")
                    ),
                    "suggested_fix": (
                        f"Migrate to '{new_key}' via localization_execute_migration"
                        if new_key else "Migrate to lowercase.with.dots format"
                    ),
                })

    if is_swift:
        for line_no, line in _iter_code_lines(content):
            if _DEBUG_CONTEXT_RE.search(line):
                continue
            # Strip any &&"..." occurrences so their inner text is not
            # re-caught by the hardcoded-string regex.
            cleaned = _SWIFT_LOC_KEY_RE.sub('""', line)
            for match in _SWIFT_HARDCODED_RE.finditer(cleaned):
                text = match.group(1).strip()
                if _looks_like_identifier(text):
                    continue
                issues.append({
                    "category": "localization",
                    "code": "LOC005",
                    "severity": "warning",
                    "line": line_no,
                    "message": f'Hardcoded user-facing string: "{text}"',
                    "suggested_fix": (
                        "Replace with &&\"key\" and add to Localizable.xcstrings"
                    ),
                })

    return issues


def _iter_code_lines(content: str):
    """Yield (1-based line number, line text) for non-comment lines.

    Skips single-line `//` comments and lines inside `/* ... */` blocks.
    Inline comments are left intact — the regexes tolerate them.
    """
    in_block_comment = False
    for idx, raw in enumerate(content.splitlines(), start=1):
        line = raw
        if in_block_comment:
            end = line.find("*/")
            if end == -1:
                continue
            line = line[end + 2 :]
            in_block_comment = False
        start = line.find("/*")
        if start != -1:
            end = line.find("*/", start + 2)
            if end == -1:
                in_block_comment = True
                line = line[:start]
            else:
                line = line[:start] + line[end + 2 :]
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        if not stripped:
            continue
        yield idx, line


def _looks_like_identifier(text: str) -> bool:
    """Filter out strings that look like identifiers, paths, or system constants."""
    if any(hint in text for hint in _IDENT_HINTS):
        return True
    if text.endswith(_SF_SYMBOL_SUFFIXES):
        return True
    if text.isupper():
        return True
    # CamelCase identifier detection — a no-space token with an uppercase
    # letter past position 0 is almost always a type or symbol name (e.g.
    # WebKitViewController, EasyPayViewController, DWButtonConfig).
    if " " not in text and any(c.isupper() for c in text[1:]):
        return True
    return False
