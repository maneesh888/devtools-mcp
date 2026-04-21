"""Core operations for Apple .xcstrings (Strings Catalog) files.

Delegates to helper modules in .scripts/ for core logic
(searching, entry creation, insertion, Arabic copy).

IMPORTANT: Never uses json.dump() on the full file to avoid 100K+ line
reformatting. Uses line-by-line insertion/removal instead.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .scripts import add_multiple_keys as _add_multiple_mod
from .scripts import check_existing_translations as _check_existing_mod
from .scripts import copy_arabic_translations as _copy_arabic_mod
from .scripts import find_old_format_keys as _find_old_format_mod

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_XCSTRINGS = os.environ.get(
    "DEVTOOLS_IOS_XCSTRINGS",
    "",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class LocalizationEntry:
    """A single localization key with its translations."""

    key: str
    english: str | None = None
    arabic: str | None = None
    extraction_state: str = "manual"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "english": self.english,
            "arabic": self.arabic,
            "extraction_state": self.extraction_state,
        }


@dataclass
class XCStringsFile:
    """Parsed representation of a .xcstrings file."""

    path: str
    source_language: str = "en"
    version: str = "1.0"
    entries: dict[str, LocalizationEntry] = field(default_factory=dict)
    _raw_data: dict = field(default_factory=dict, repr=False)

    @property
    def total_keys(self) -> int:
        return len(self.entries)

    @property
    def missing_arabic(self) -> list[LocalizationEntry]:
        return [e for e in self.entries.values() if not e.arabic]

    @property
    def missing_english(self) -> list[LocalizationEntry]:
        return [e for e in self.entries.values() if not e.english]


# ---------------------------------------------------------------------------
# Key format helpers — delegates to find_old_format_keys.py
# ---------------------------------------------------------------------------


def is_old_format(key: str) -> bool:
    """Check if a key uses the old capital-case format.

    Delegates to find_old_format_keys.is_old_format_key().
    """
    return _find_old_format_mod.is_old_format_key(key)


def to_new_format(key: str) -> str:
    """Convert an old format key to new lowercase.with.dots format.

    Delegates to find_old_format_keys.suggest_new_format_key().
    """
    return _find_old_format_mod.suggest_new_format_key(key)


def validate_key_format(key: str) -> tuple[bool, str]:
    """Validate a key follows the new format conventions.

    Returns (is_valid, error_message).
    """
    if not key:
        return False, "Key cannot be empty"
    if key != key.lower():
        return False, f"Key must be lowercase: '{key}'"
    if " " in key:
        return False, f"Key must not contain spaces, use dots: '{key}'"
    if re.search(r"[^a-z0-9.]", key):
        return False, f"Key should only contain a-z, 0-9, and dots: '{key}'"
    if key.startswith(".") or key.endswith("."):
        return False, f"Key should not start or end with a dot: '{key}'"
    return True, ""


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


_XCSTRINGS_SEARCH_ROOTS = [
    # Add project-specific search paths here
]

_discovered_path: str | None = None


def _resolve_path(xcstrings_path: str = "") -> str:
    """Resolve the xcstrings file path.

    Priority: explicit arg > env var > auto-discovery in known locations.
    """
    global _discovered_path

    path = xcstrings_path or _DEFAULT_XCSTRINGS
    if path:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"xcstrings file not found: {path}")
        return path

    # Auto-discover: use cached result if available
    if _discovered_path:
        return _discovered_path

    for root in _XCSTRINGS_SEARCH_ROOTS:
        candidate = os.path.join(root, "Localizable.xcstrings")
        if os.path.isfile(candidate):
            _discovered_path = candidate
            return candidate

    raise FileNotFoundError(
        "No xcstrings path provided and DEVTOOLS_IOS_XCSTRINGS env var not set. "
        "Auto-discovery also failed. Pass the path to your Localizable.xcstrings file."
    )


def _load_raw(xcstrings_path: str = "") -> tuple[str, dict]:
    """Load raw JSON data from the xcstrings file.

    Returns (resolved_path, raw_data).
    """
    path = _resolve_path(xcstrings_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return path, data


def read_xcstrings(xcstrings_path: str = "") -> XCStringsFile:
    """Parse a .xcstrings file into a structured representation."""
    path, data = _load_raw(xcstrings_path)

    xcfile = XCStringsFile(
        path=path,
        source_language=data.get("sourceLanguage", "en"),
        version=data.get("version", "1.0"),
        _raw_data=data,
    )

    strings = data.get("strings", {})
    for key, value in strings.items():
        localizations = value.get("localizations", {})
        en_val = None
        ar_val = None

        en_block = localizations.get("en", {})
        if en_block:
            en_unit = en_block.get("stringUnit", {})
            en_val = en_unit.get("value") or None

        ar_block = localizations.get("ar", {})
        if ar_block:
            ar_unit = ar_block.get("stringUnit", {})
            ar_val = ar_unit.get("value") or None

        xcfile.entries[key] = LocalizationEntry(
            key=key,
            english=en_val,
            arabic=ar_val,
            extraction_state=value.get("extractionState", "manual"),
        )

    return xcfile


# ---------------------------------------------------------------------------
# Check / Search — delegates to check_existing_translations.py
# ---------------------------------------------------------------------------


def check_key(key: str, xcstrings_path: str = "") -> dict:
    """Check if a key exists and return its translation status.

    Also detects old format keys (any uppercase letters) and recommends
    migration to lowercase.with.dots format per the localization guide.

    Uses check_existing_translations.search_by_key() for the lookup.
    """
    _path, data = _load_raw(xcstrings_path)
    strings = data.get("strings", {})

    old_fmt_mod = _find_old_format_mod
    is_old = old_fmt_mod.is_old_format_key(key)

    # Build old format info if applicable
    old_format_info = {}
    if is_old:
        new_key = old_fmt_mod.suggest_new_format_key(key)
        new_exists = old_fmt_mod.check_new_key_exists(new_key, data)
        old_format_info = {
            "is_old_format": True,
            "suggested_new_key": new_key,
            "new_key_exists": new_exists,
            "migration_recommendation": (
                f"Old format key. New key '{new_key}' already exists. "
                f"Migrate all code references from '{key}' to '{new_key}', "
                f"then remove old key '{key}'."
                if new_exists
                else f"Old format key. Create new key '{new_key}' with "
                f"translations copied from '{key}', migrate code, then remove '{key}'."
            ),
        }
    else:
        old_format_info = {"is_old_format": False}

        # Reverse check: if this is a new format key, find any old format
        # duplicates that still exist in xcstrings and should be removed.
        old_duplicates = []
        for existing_key in strings:
            if old_fmt_mod.is_old_format_key(existing_key):
                if old_fmt_mod.suggest_new_format_key(existing_key) == key:
                    old_duplicates.append(existing_key)
        if old_duplicates:
            old_format_info["old_format_duplicates"] = old_duplicates
            old_format_info["cleanup_recommendation"] = (
                f"Old format key(s) {old_duplicates} map to '{key}' and should "
                f"be migrated. Update all code references to use '{key}', "
                f"then remove the old key(s)."
            )

    if key not in strings:
        return {
            "exists": False,
            "key": key,
            "english": None,
            "arabic": None,
            "has_english": False,
            "has_arabic": False,
            **old_format_info,
        }

    localizations = strings[key].get("localizations", {})
    en = localizations.get("en", {}).get("stringUnit", {}).get("value", "")
    ar = localizations.get("ar", {}).get("stringUnit", {}).get("value", "")

    return {
        "exists": True,
        "key": key,
        "english": en or None,
        "arabic": ar or None,
        "has_english": bool(en),
        "has_arabic": bool(ar),
        **old_format_info,
    }


def search_keys(query: str, xcstrings_path: str = "") -> list[dict]:
    """Search for keys matching a query string.

    Delegates to check_existing_translations.search_by_key() and
    search_by_text() from the existing script.
    """
    _path, data = _load_raw(xcstrings_path)
    strings = data.get("strings", {})

    mod = _check_existing_mod

    # Search both by key name and by text value, combine results
    key_results = mod.search_by_key(strings, query)
    text_results = mod.search_by_text(strings, query)

    # Merge, deduplicate by key name
    seen_keys = {r["key"] for r in key_results}
    combined = list(key_results)
    for r in text_results:
        if r["key"] not in seen_keys:
            combined.append(r)
            seen_keys.add(r["key"])

    return combined


# ---------------------------------------------------------------------------
# Write operations — delegates to add_multiple_keys.py for entry creation
# and insertion. Line-by-line to preserve formatting.
# ---------------------------------------------------------------------------


def _add_key_internal(
    key: str,
    english: str,
    arabic: str = "",
    xcstrings_path: str = "",
) -> dict:
    """Internal: add a key with optional Arabic. Only called by execute_migration."""
    path = _resolve_path(xcstrings_path)

    valid, err = validate_key_format(key)
    if not valid:
        return {"success": False, "error": err}

    existing = check_key(key, path)
    if existing["exists"]:
        return {"success": False, "error": f"Key '{key}' already exists", "existing": existing}

    mod = _add_multiple_mod

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entry = mod.create_entry(key, english, arabic or "")
    insert_at = mod.find_insertion_point(lines, key)

    if insert_at is not None:
        lines.insert(insert_at, entry + "\n")
    else:
        return {"success": False, "error": "Could not find insertion point in xcstrings file"}

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return {
        "success": True,
        "key": key,
        "english": english,
        "arabic": arabic or None,
        "message": f"Added key '{key}' to {Path(path).name}",
    }


def add_key(
    key: str,
    english: str,
    arabic: str | None = None,
    xcstrings_path: str = "",
) -> dict:
    """Add a new localization key with English only.

    Arabic is NEVER added via this function. Arabic enters xcstrings
    only via execute_migration (copies from old format key during
    verification) or by the translation team editing xcstrings directly.

    Args:
        key: The localization key (lowercase.with.dots format).
        english: English translation value.
        arabic: Rejected — exists for API compat but always refused.
        xcstrings_path: Path to Localizable.xcstrings.
    """
    # HARD GUARD: Reject any caller-provided Arabic.
    if arabic:
        return {
            "success": False,
            "error": (
                "Arabic parameter rejected. Arabic must not be added during "
                "development. Use execute_migration to copy Arabic from an "
                "old format key during verification, or let the translation "
                "team add it. Call add_key without arabic."
            ),
        }

    # HARD GUARD: Reject keys that don't follow the naming convention.
    is_valid, fmt_error = validate_key_format(key)
    if not is_valid:
        suggested = to_new_format(key)
        return {
            "success": False,
            "error": f"Invalid key format: {fmt_error}",
            "rejected_key": key,
            "suggested_key": suggested,
            "usage_example": f'&&"{suggested}"',
            "rule": "Keys must be lowercase.with.dots (e.g. 'whatsapp.number', not 'WhatsApp Number')",
        }

    # Check for existing keys with the same English text.
    # If found, reuse the existing key instead of creating a duplicate.
    path = _resolve_path(xcstrings_path)
    _path, data = _load_raw(path)
    strings = data.get("strings", {})
    matches = []
    english_lower = english.lower()
    for existing_key, entry in strings.items():
        localizations = entry.get("localizations", {})
        en_val = localizations.get("en", {}).get("stringUnit", {}).get("value", "")
        if en_val.lower() == english_lower:
            has_ar = bool(
                localizations.get("ar", {}).get("stringUnit", {}).get("value", "")
            )
            matches.append({
                "key": existing_key,
                "english": en_val,
                "has_arabic": has_ar,
            })

    if matches:
        # Prefer new-format keys over old-format
        old_fmt_mod = _find_old_format_mod
        new_fmt = [m for m in matches if not old_fmt_mod.is_old_format_key(m["key"])]
        old_fmt = [m for m in matches if old_fmt_mod.is_old_format_key(m["key"])]

        return {
            "success": False,
            "error": "Existing key(s) found with same English text. Reuse instead of creating duplicate.",
            "existing_keys": new_fmt + old_fmt,
            "recommendation": (
                f"Use existing key '{(new_fmt or old_fmt)[0]['key']}' "
                f"instead of creating '{key}'."
                + (
                    f" Old format key '{old_fmt[0]['key']}' also exists — "
                    f"use execute_migration to migrate it."
                    if old_fmt and new_fmt
                    else ""
                )
            ),
        }

    return _add_key_internal(key, english, "", xcstrings_path)


def add_keys_bulk(
    keys: list[dict],
    xcstrings_path: str = "",
) -> dict:
    """Add multiple localization keys at once.

    Uses add_multiple_keys.create_entry() and find_insertion_point()
    for each key.
    """
    results = {"added": [], "failed": [], "total": len(keys)}

    for entry in keys:
        key = entry.get("key", "")
        english = entry.get("english", "")
        arabic = entry.get("arabic")

        if not key or not english:
            results["failed"].append({
                "key": key,
                "error": "Both 'key' and 'english' are required",
            })
            continue

        result = add_key(key, english, arabic, xcstrings_path)
        if result["success"]:
            results["added"].append(result)
        else:
            results["failed"].append({"key": key, "error": result.get("error", "Unknown error")})

    results["added_count"] = len(results["added"])
    results["failed_count"] = len(results["failed"])
    results["success"] = results["failed_count"] == 0

    return results


# ---------------------------------------------------------------------------
# Copy Arabic translation — delegates to copy_arabic_translations.py
# NOTE: Only uses copy_arabic() function, NOT save_localizable()
# (save_localizable uses json.dump which reformats the entire file)
# ---------------------------------------------------------------------------


def copy_arabic_translation(
    target_key: str,
    source_key: str,
    xcstrings_path: str = "",
) -> dict:
    """Copy Arabic translation from one key to another.

    Uses copy_arabic_translations.copy_arabic() for the copy logic,
    but writes back using line-by-line approach (NOT json.dump).

    Args:
        target_key: Key to receive the Arabic translation.
        source_key: Key to copy Arabic from.
        xcstrings_path: Path to Localizable.xcstrings.
    """
    path = _resolve_path(xcstrings_path)
    mod = _copy_arabic_mod

    # Load data, use script's copy_arabic() to do the copy in memory
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    success, message = mod.copy_arabic(data, target_key, source_key)

    if not success:
        return {"success": False, "error": message}

    # Write back using line-by-line approach instead of json.dump
    # Read the raw lines, find the target key, and insert/update the Arabic block
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find the target key's localization block and add/update Arabic
    ar_value = message  # copy_arabic returns the Arabic value on success
    target_pattern = re.compile(rf'^\s+"{re.escape(target_key)}"\s*:\s*\{{')
    target_start = None

    for i, line in enumerate(lines):
        if target_pattern.match(line):
            target_start = i
            break

    if target_start is None:
        return {"success": False, "error": f"Could not locate key '{target_key}' in file"}

    # Find the "localizations" block within this key
    loc_line = None
    for i in range(target_start, min(target_start + 10, len(lines))):
        if '"localizations"' in lines[i]:
            loc_line = i
            break

    if loc_line is None:
        return {"success": False, "error": f"Could not find localizations block for '{target_key}'"}

    # Check if Arabic block already exists
    ar_exists = False
    for i in range(loc_line, min(loc_line + 15, len(lines))):
        if '"ar"' in lines[i]:
            ar_exists = True
            # Find and update the value line
            for j in range(i, min(i + 5, len(lines))):
                if '"value"' in lines[j]:
                    escaped = ar_value.replace('"', '\\"')
                    lines[j] = re.sub(
                        r'"value"\s*:\s*"[^"]*"',
                        f'"value" : "{escaped}"',
                        lines[j],
                    )
                    break
            break

    if not ar_exists:
        # Insert Arabic block before the "en" block
        for i in range(loc_line, min(loc_line + 15, len(lines))):
            if '"en"' in lines[i]:
                escaped = ar_value.replace('"', '\\"')
                ar_block = (
                    '        "ar" : {\n'
                    '          "stringUnit" : {\n'
                    '            "state" : "translated",\n'
                    f'            "value" : "{escaped}"\n'
                    '          }\n'
                    '        },\n'
                )
                lines.insert(i, ar_block)
                break

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return {
        "success": True,
        "target_key": target_key,
        "source_key": source_key,
        "arabic_value": ar_value,
        "message": f"Copied Arabic from '{source_key}' to '{target_key}'",
    }


# ---------------------------------------------------------------------------
# Remove key (line-by-line, no script equivalent exists for this)
# ---------------------------------------------------------------------------


def remove_key(key: str, xcstrings_path: str = "") -> dict:
    """Remove a localization key from the xcstrings file.

    Uses line-by-line removal to preserve formatting.
    Should only be called after verifying the key has zero usage in code.
    """
    path = _resolve_path(xcstrings_path)

    existing = check_key(key, path)
    if not existing["exists"]:
        return {"success": False, "error": f"Key '{key}' not found in xcstrings file"}

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    key_pattern = re.compile(rf'^\s+"{re.escape(key)}"\s*:\s*\{{')
    start_line = None

    for i, line in enumerate(lines):
        if key_pattern.match(line):
            start_line = i
            break

    if start_line is None:
        return {"success": False, "error": f"Could not locate key '{key}' in file"}

    # Find closing brace at same depth
    depth = 0
    end_line = start_line
    for i in range(start_line, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0:
            end_line = i
            break

    # Handle trailing comma
    if lines[end_line].rstrip().endswith(","):
        pass
    elif end_line + 1 < len(lines) and lines[end_line + 1].strip() == "":
        end_line += 1

    del lines[start_line : end_line + 1]

    # Clean up dangling comma before closing brace
    if start_line > 0 and start_line < len(lines):
        prev = lines[start_line - 1].rstrip()
        next_stripped = lines[start_line].strip() if start_line < len(lines) else ""
        if prev.endswith(",") and next_stripped.startswith("}"):
            lines[start_line - 1] = prev[:-1] + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return {
        "success": True,
        "key": key,
        "message": f"Removed key '{key}' from {Path(path).name}",
    }
