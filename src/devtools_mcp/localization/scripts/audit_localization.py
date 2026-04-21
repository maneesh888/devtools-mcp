"""Extract localization keys and detect hardcoded strings in source files.

Supports both Swift (&&"key") and Objective-C (NSLocalizedString) patterns.
Used by auditor.py for file-level localization auditing.
"""

from __future__ import annotations

import re


def extract_localization_keys(source_file: str) -> list[str]:
    """Extract all localization key patterns from a Swift or Objective-C file.

    Supports:
    - Swift: &&"key"
    - ObjC: NSLocalizedString(@"key", ...)
    - ObjC: localizedString:@"key"
    """
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()

    keys = []

    # Swift: &&"key" patterns
    swift_pattern = r'&&"([^"]+)"'
    keys.extend(re.findall(swift_pattern, content))

    # ObjC: NSLocalizedString(@"key", ...)
    objc_nsl_pattern = r'NSLocalizedString\s*\(\s*@"([^"]+)"'
    keys.extend(re.findall(objc_nsl_pattern, content))

    # ObjC: localizedString:@"key" (common in custom localization helpers)
    objc_helper_pattern = r'localizedString\s*:\s*@"([^"]+)"'
    keys.extend(re.findall(objc_helper_pattern, content))

    return keys


def find_hardcoded_strings(source_file: str) -> list[tuple[int, str]]:
    """Find potential hardcoded user-facing strings in source code.

    Returns list of (line_number, string_value) tuples.
    """
    with open(source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    is_objc = source_file.endswith(('.m', '.mm'))
    hardcoded = []

    # Swift: "Text" not preceded by &&
    swift_pattern = r'(?<!&)"([A-Z][a-zA-Z\s]+)"'
    # ObjC: @"Text" not inside NSLocalizedString
    objc_pattern = r'(?<!NSLocalizedString\s*\(\s*)@"([A-Z][a-zA-Z\s]+)"'

    pattern = objc_pattern if is_objc else swift_pattern

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('#import') or stripped.startswith('import '):
            continue

        matches = re.findall(pattern, line)
        for match in matches:
            if len(match) > 3:
                hardcoded.append((line_num, match))

    return hardcoded


def check_key_status(key: str, localizable_data: dict) -> str:
    """Check if a key exists and has both EN and AR translations.

    Returns one of: "OK", "MISSING_KEY", "MISSING_EN", "MISSING_AR".
    """
    strings = localizable_data.get("strings", {})

    if key not in strings:
        return "MISSING_KEY"

    localizations = strings[key].get("localizations", {})
    en_value = localizations.get("en", {}).get("stringUnit", {}).get("value", "")
    ar_value = localizations.get("ar", {}).get("stringUnit", {}).get("value", "")

    if not en_value:
        return "MISSING_EN"
    if not ar_value:
        return "MISSING_AR"

    return "OK"
