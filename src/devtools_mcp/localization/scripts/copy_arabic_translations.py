"""Copy Arabic translations between keys in xcstrings data.

Operates on in-memory data only. The caller handles file I/O
using line-by-line writes (never json.dump on the full file).
"""

from __future__ import annotations


def copy_arabic(data: dict, target_key: str, source_key: str) -> tuple[bool, str]:
    """Copy Arabic translation from source_key to target_key.

    Mutates the data dict in place. Returns (success, message) where
    message is the Arabic value on success, or an error string on failure.
    """
    strings = data.get("strings", {})

    if source_key not in strings:
        return False, f"Source key '{source_key}' not found"

    if target_key not in strings:
        return False, f"Target key '{target_key}' not found"

    source_ar = (
        strings[source_key]
        .get("localizations", {})
        .get("ar", {})
        .get("stringUnit", {})
    )

    if not source_ar or not source_ar.get("value"):
        return False, f"Source key '{source_key}' has no Arabic translation"

    # Copy Arabic to target
    if "ar" not in strings[target_key].get("localizations", {}):
        strings[target_key]["localizations"]["ar"] = {}

    strings[target_key]["localizations"]["ar"]["stringUnit"] = {
        "state": source_ar.get("state", "translated"),
        "value": source_ar.get("value", ""),
    }

    ar_value = source_ar.get("value", "")
    return True, ar_value
