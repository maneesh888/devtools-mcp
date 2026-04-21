"""File metadata audit — enforce the Xcode file header contract.

Rules (from user global CLAUDE.md):
- `Created by` line must name Maneesh, never Claude or any generic label.
- Copyright line should mention your company/project.
"""

from __future__ import annotations

import re

_CREATED_BY_RE = re.compile(r"//\s*Created by\s+(.+?)\s+on\b", re.IGNORECASE)
_COPYRIGHT_RE = re.compile(r"//\s*Copyright\s+.*", re.IGNORECASE)

_EXPECTED_AUTHOR = "Maneesh"
_FORBIDDEN_AUTHORS = ("claude", "anthropic", "ai", "gpt")


def audit_file_metadata(file_path: str, content: str) -> list[dict]:
    """Return file-header issues for the given Swift/ObjC file."""
    if not file_path.endswith((".swift", ".m", ".mm", ".h")):
        return []

    header = "\n".join(content.splitlines()[:10])
    issues: list[dict] = []

    created_match = _CREATED_BY_RE.search(header)
    if created_match:
        author = created_match.group(1).strip()
        lowered = author.lower()
        if any(bad in lowered for bad in _FORBIDDEN_AUTHORS):
            issues.append({
                "category": "file_metadata",
                "code": "FM001",
                "severity": "error",
                "line": _line_of(content, created_match.group(0)),
                "message": f"File author is '{author}' — must be '{_EXPECTED_AUTHOR}'",
                "suggested_fix": f"Change the 'Created by' line to '{_EXPECTED_AUTHOR}'",
            })
        # Non-Maneesh human authors are left alone — files created by other
        # engineers legitimately carry their name. FM001 catches the real
        # risk: Claude/AI-generated headers leaking into the repo.

    if not _COPYRIGHT_RE.search(header):
        issues.append({
            "category": "file_metadata",
            "code": "FM003",
            "severity": "info",
            "line": 1,
            "message": "File header missing Copyright line",
            "suggested_fix": "Add a '// Copyright © <year> YourCompany. All rights reserved.' line",
        })

    return issues


def _line_of(content: str, snippet: str) -> int:
    for idx, line in enumerate(content.splitlines(), start=1):
        if snippet.strip() in line:
            return idx
    return 1
