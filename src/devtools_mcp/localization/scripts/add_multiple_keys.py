"""Create and insert localization entries into xcstrings files.

Provides line-by-line insertion to preserve Xcode's formatting.
Never uses json.dump on the full file.
"""

from __future__ import annotations


def create_entry(key: str, en_value: str, ar_value: str = "") -> str:
    """Create a JSON entry block for a localization key.

    Returns a string matching Xcode's xcstrings formatting (4-space indent,
    trailing comma). The caller is responsible for inserting it at the
    correct position in the file.
    """
    en_escaped = en_value.replace('"', '\\"')
    ar_escaped = ar_value.replace('"', '\\"')

    if ar_value:
        return (
            f'    "{key}" : {{\n'
            f'      "extractionState" : "manual",\n'
            f'      "localizations" : {{\n'
            f'        "ar" : {{\n'
            f'          "stringUnit" : {{\n'
            f'            "state" : "translated",\n'
            f'            "value" : "{ar_escaped}"\n'
            f'          }}\n'
            f'        }},\n'
            f'        "en" : {{\n'
            f'          "stringUnit" : {{\n'
            f'            "state" : "translated",\n'
            f'            "value" : "{en_escaped}"\n'
            f'          }}\n'
            f'        }}\n'
            f'      }}\n'
            f'    }},'
        )
    else:
        return (
            f'    "{key}" : {{\n'
            f'      "extractionState" : "manual",\n'
            f'      "localizations" : {{\n'
            f'        "en" : {{\n'
            f'          "stringUnit" : {{\n'
            f'            "state" : "translated",\n'
            f'            "value" : "{en_escaped}"\n'
            f'          }}\n'
            f'        }}\n'
            f'      }}\n'
            f'    }},'
        )


def find_insertion_point(lines: list[str], key: str) -> int | None:
    """Find the line index where a new entry should be inserted.

    Maintains alphabetical order among existing entries. Returns None
    if no suitable anchor point is found (e.g. empty strings block).

    The function looks for lines matching Xcode's entry pattern:
    4-space indent key followed by ` : {`. It finds the right position
    alphabetically and returns the line after the previous entry's
    closing `},`.
    """
    last_entry_end = None
    for i, line in enumerate(lines):
        if line.strip().startswith('"') and ' : {' in line:
            existing_key = line.strip().split('"')[1]
            if existing_key > key:
                # Find the closing brace of previous entry
                j = i - 1
                while j >= 0:
                    if lines[j].strip() == '},':
                        return j + 1
                    j -= 1
        # Track the last entry's closing brace for end-of-list insertion
        if lines[i].strip() == '},':
            last_entry_end = i

    # Key goes at the end (alphabetically after all existing keys)
    if last_entry_end is not None:
        return last_entry_end + 1
    return None
