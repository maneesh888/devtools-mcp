"""Localization key migration for iOS projects.

Provides execute_migration and remove_old_key. Discovery and analysis
tools were removed because the agent handles those natively using
summary + check_key + Grep.

Migration workflow:
1. Agent identifies old format keys (via summary or check_key)
2. Agent gets user approval
3. execute_migration creates new key and copies translations
4. Agent updates code references
5. remove_old_key verifies zero usage and cleans up
"""

from __future__ import annotations

from .auditor import find_key_usage
from .scripts import find_old_format_keys as _find_old_format_mod
from .xcstrings import (
    _load_raw,
    check_key,
    copy_arabic_translation,
    remove_key,
)


# ---------------------------------------------------------------------------
# Migration execution
# ---------------------------------------------------------------------------


def execute_migration(
    old_key: str,
    project_path: str,
    xcstrings_path: str = "",
) -> dict:
    """Execute a key migration from old to new format.

    1. Creates the new format key (if it doesn't exist) with translations
    2. Copies Arabic using copy_arabic_translations.copy_arabic()
    3. Reports files needing code changes (does NOT modify source code)
    4. Does NOT remove the old key (caller verifies zero usage first)
    """
    old_fmt_mod = _find_old_format_mod
    _path, data = _load_raw(xcstrings_path)
    strings = data.get("strings", {})

    if old_key not in strings:
        return {"success": False, "error": f"Key '{old_key}' not found"}

    new_key = old_fmt_mod.suggest_new_format_key(old_key)
    steps_completed: list[str] = []

    # Get old key translations
    localizations = strings[old_key].get("localizations", {})
    old_en = localizations.get("en", {}).get("stringUnit", {}).get("value", "")
    old_ar = localizations.get("ar", {}).get("stringUnit", {}).get("value", "")

    # Step 1: Create new key if needed
    new_check = check_key(new_key, xcstrings_path)
    if not new_check["exists"]:
        from .xcstrings import _add_key_internal
        add_result = _add_key_internal(
            key=new_key,
            english=old_en,
            arabic=old_ar if old_ar else "",
            xcstrings_path=xcstrings_path,
        )
        if not add_result["success"]:
            return {
                "success": False,
                "error": f"Failed to create new key: {add_result.get('error')}",
            }
        steps_completed.append(f"Created new key '{new_key}' with translations")
    else:
        steps_completed.append(f"New key '{new_key}' already exists")

        # If new key exists but missing Arabic, copy it from old key
        if not new_check["has_arabic"] and old_ar:
            copy_result = copy_arabic_translation(new_key, old_key, xcstrings_path)
            if copy_result["success"]:
                steps_completed.append(f"Copied Arabic translation to '{new_key}'")
            else:
                steps_completed.append(
                    f"Warning: could not copy Arabic: {copy_result.get('error')}"
                )

    # Step 2: Find all code locations using script's check_key_usage
    usage_count, locations = old_fmt_mod.check_key_usage(old_key, project_path)
    steps_completed.append(f"Found {usage_count} code location(s) using '{old_key}'")

    usages = []
    for loc in locations:
        parts = loc.split(":", 2)
        if len(parts) >= 3:
            usages.append({
                "file": parts[0],
                "line": int(parts[1]) if parts[1].isdigit() else 0,
                "line_content": parts[2].strip(),
            })

    return {
        "success": True,
        "old_key": old_key,
        "new_key": new_key,
        "steps_completed": steps_completed,
        "files_to_update": usages,
        "next_steps": [
            f"Update all code references from '{old_key}' to '{new_key}'",
            f"Verify zero usage of '{old_key}' in both .swift and .m files",
            f"Remove old key '{old_key}' from Localizable.xcstrings",
        ],
        "message": (
            "New key is ready. Update the code references listed in 'files_to_update', "
            "then call remove_old_key after verifying zero usage."
        ),
    }


def remove_old_key(
    old_key: str,
    project_path: str,
    xcstrings_path: str = "",
) -> dict:
    """Remove an old format key after verifying zero usage.

    Safety check: refuses to remove if key is still referenced in code.
    Uses find_key_usage (grep-based) for the check.
    """
    usages = find_key_usage(old_key, project_path)
    if usages:
        return {
            "success": False,
            "error": f"Key '{old_key}' is still used in {len(usages)} location(s). "
                     "Update all references before removing.",
            "remaining_usages": usages,
        }

    result = remove_key(old_key, xcstrings_path)
    return result
