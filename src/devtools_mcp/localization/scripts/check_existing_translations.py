"""Search existing translations by key name or English text.

Used by xcstrings.search_keys() to find matching entries without
loading the entire file into the agent's context.
"""

from __future__ import annotations


def search_by_key(strings_dict: dict, search_key: str) -> list[dict]:
    """Search for keys similar to search_key.

    Normalizes both the search term and existing keys by stripping
    dots and spaces and lowercasing, so "Account Number" matches
    "account.number".
    """
    results = []
    search_lower = search_key.lower().replace('.', '').replace(' ', '')

    for key, value in strings_dict.items():
        key_lower = key.lower().replace('.', '').replace(' ', '')

        if search_lower in key_lower or key_lower in search_lower:
            localizations = value.get("localizations", {})
            en = localizations.get("en", {}).get("stringUnit", {}).get("value", "")
            ar = localizations.get("ar", {}).get("stringUnit", {}).get("value", "")

            results.append({
                "key": key,
                "en": en,
                "ar": ar,
                "has_ar": bool(ar),
            })

    return results


def search_by_text(strings_dict: dict, search_text: str) -> list[dict]:
    """Search for entries whose English value contains search_text."""
    results = []
    search_lower = search_text.lower()

    for key, value in strings_dict.items():
        localizations = value.get("localizations", {})
        en = localizations.get("en", {}).get("stringUnit", {}).get("value", "")
        ar = localizations.get("ar", {}).get("stringUnit", {}).get("value", "")

        if search_lower in en.lower():
            results.append({
                "key": key,
                "en": en,
                "ar": ar,
                "has_ar": bool(ar),
            })

    return results
