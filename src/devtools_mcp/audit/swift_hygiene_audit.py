"""Swift hygiene audit — flag patterns that commonly leak into commits.

Scope: Swift only. Covers `print()`, `try!`, `fatalError()`, and TODO/FIXME
markers. Force-unwrap detection is intentionally omitted in v1 because it
has too many false positives without proper parsing.
"""

from __future__ import annotations

import re

_PRINT_RE = re.compile(r"(?<![.\w])print\s*\(")
_TRY_BANG_RE = re.compile(r"\btry!\s")
_FATAL_ERROR_RE = re.compile(r"\bfatalError\s*\(")
_TODO_RE = re.compile(r"//\s*(TODO|FIXME)[:\s]", re.IGNORECASE)


def audit_swift_hygiene(file_path: str, content: str) -> list[dict]:
    """Return Swift hygiene issues for the given file."""
    if not file_path.endswith(".swift"):
        return []

    issues: list[dict] = []

    for line_no, line in _iter_all_lines(content):
        stripped = line.lstrip()

        if _TODO_RE.search(line):
            issues.append({
                "category": "swift_hygiene",
                "code": "SH001",
                "severity": "warning",
                "line": line_no,
                "message": "TODO/FIXME marker in code",
                "suggested_fix": "Resolve before commit, or track in the issue tracker and remove the marker",
            })

        # Skip other checks if the whole line is a comment
        if stripped.startswith("//"):
            continue
        line_no_comment = _strip_inline_comment(line)

        if _PRINT_RE.search(line_no_comment):
            issues.append({
                "category": "swift_hygiene",
                "code": "SH002",
                "severity": "warning",
                "line": line_no,
                "message": "print() left in source",
                "suggested_fix": "Remove or replace with debugPrint / project logger",
            })

        if _TRY_BANG_RE.search(line_no_comment):
            issues.append({
                "category": "swift_hygiene",
                "code": "SH003",
                "severity": "warning",
                "line": line_no,
                "message": "try! used — will crash on throw",
                "suggested_fix": "Handle the error with try/catch or try?",
            })

        if _FATAL_ERROR_RE.search(line_no_comment):
            issues.append({
                "category": "swift_hygiene",
                "code": "SH004",
                "severity": "warning",
                "line": line_no,
                "message": "fatalError() used — will crash the app",
                "suggested_fix": "Prefer assertionFailure or return/throw where possible",
            })

    return issues


def _iter_all_lines(content: str):
    for idx, line in enumerate(content.splitlines(), start=1):
        yield idx, line


def _strip_inline_comment(line: str) -> str:
    idx = line.find("//")
    if idx == -1:
        return line
    return line[:idx]
