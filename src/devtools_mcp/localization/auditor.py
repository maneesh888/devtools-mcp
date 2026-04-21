"""Localization usage search for iOS projects.

Only provides find_key_usage, which is needed by remove_old_key's
safety check. Full auditing (missing keys, hardcoded strings, etc.)
is handled by the agent reading files and calling check_key directly.
"""

from __future__ import annotations

import os
import subprocess


def find_key_usage(
    key: str,
    project_path: str,
    file_extensions: tuple[str, ...] = (".swift", ".m", ".mm"),
) -> list[dict]:
    """Find all usages of a localization key across the project.

    Uses grep to search both Swift and Objective-C files.
    """
    if not os.path.isdir(project_path):
        raise NotADirectoryError(f"Project directory not found: {project_path}")

    usages: list[dict] = []

    include_flags = []
    for ext in file_extensions:
        include_flags.extend(["--include", f"*{ext}"])

    try:
        proc = subprocess.run(
            ["grep", "-rn", f'"{key}"', project_path] + include_flags,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.strip().split("\n"):
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    usages.append({
                        "file": parts[0],
                        "line": int(parts[1]) if parts[1].isdigit() else 0,
                        "line_content": parts[2].strip(),
                    })
    except Exception:
        pass

    return usages
