"""Detect and convert old-format localization keys.

Old format: capital-case with spaces (e.g. "Select Nationality")
New format: lowercase.with.dots (e.g. "select.nationality")

Also provides grep-based usage counting for migration planning.
"""

from __future__ import annotations

import subprocess


def is_old_format_key(key: str) -> bool:
    """Check if a key uses the old format (any uppercase letters).

    Per naming rules, keys must be lowercase with dots (a-z, 0-9, .).
    Any key containing uppercase letters is old format.
    """
    if not key:
        return False
    return key != key.lower()


def suggest_new_format_key(old_key: str) -> str:
    """Convert an old-format key to lowercase.with.dots.

    "Select Nationality" -> "select.nationality"
    "Remove"             -> "remove"
    "AccountNumber"      -> "accountnumber"
    """
    return old_key.lower().replace(' ', '.')


def check_key_usage(
    old_key: str, project_path: str
) -> tuple[int, list[str]]:
    """Count usages of a key in Swift and Objective-C files via grep.

    Returns (count, list_of_grep_lines).
    """
    try:
        result = subprocess.run(
            [
                "grep", "-rn", f'"{old_key}"', project_path,
                "--include=*.swift", "--include=*.m",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            matches = result.stdout.strip().split('\n')
            return len(matches), matches
        return 0, []
    except Exception:
        return 0, []


def check_new_key_exists(new_key: str, localizable_data: dict) -> bool:
    """Check if the new-format key already exists in xcstrings data."""
    strings = localizable_data.get("strings", {})
    return new_key in strings
