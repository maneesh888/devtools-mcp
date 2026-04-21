"""Design system audit — flag hardcoded colors and system fonts that
should be sourced from your project's design system.

Scope: Swift (UIKit + SwiftUI). Objective-C is skipped for v1.
"""

from __future__ import annotations

import re

# UIColor / Color stock constants that should be replaced with design system colors
_STOCK_COLOR_NAMES = (
    "red", "blue", "green", "yellow", "orange", "purple",
    "pink", "brown", "cyan", "magenta", "black", "white",
    "gray", "grey", "lightGray", "darkGray",
)
_STOCK_COLOR_RE = re.compile(
    r"\b(?:UIColor|Color)\s*\.\s*(" + "|".join(_STOCK_COLOR_NAMES) + r")\b"
)

# Raw RGB / hex color literals
_RGB_COLOR_RE = re.compile(
    r"\b(?:UIColor|Color)\s*\(\s*red:\s*[\d.]+"
)
_HEX_COLOR_INIT_RE = re.compile(r"\b(?:UIColor|Color)\s*\(\s*hex:")

# System fonts that should use custom typography extensions
_SYSTEM_FONT_RE = re.compile(
    r"\bUIFont\s*\.\s*(systemFont|boldSystemFont|italicSystemFont)\b"
)
_SWIFTUI_SYSTEM_FONT_RE = re.compile(r"\bFont\s*\.\s*system\s*\(")


def audit_design_system(file_path: str, content: str) -> list[dict]:
    """Return design-system issues for the given Swift file."""
    if not file_path.endswith(".swift"):
        return []

    issues: list[dict] = []

    for line_no, line in _iter_code_lines(content):
        for match in _STOCK_COLOR_RE.finditer(line):
            issues.append({
                "category": "design_system",
                "code": "DS001",
                "severity": "warning",
                "line": line_no,
                "message": (
                    f"Stock color '{match.group(0)}' used instead of design system color"
                ),
                "suggested_fix": (
                    "Use a named design system color (e.g. from your color palette)"
                ),
            })

        if _RGB_COLOR_RE.search(line):
            issues.append({
                "category": "design_system",
                "code": "DS002",
                "severity": "warning",
                "line": line_no,
                "message": "Raw RGB color literal used instead of design system color",
                "suggested_fix": "Move the color into your design system and reference by name",
            })

        if _HEX_COLOR_INIT_RE.search(line):
            issues.append({
                "category": "design_system",
                "code": "DS003",
                "severity": "warning",
                "line": line_no,
                "message": "Hex color literal used instead of design system color",
                "suggested_fix": "Move the color into your design system and reference by name",
            })

        if _SYSTEM_FONT_RE.search(line):
            issues.append({
                "category": "design_system",
                "code": "DS004",
                "severity": "warning",
                "line": line_no,
                "message": "UIFont.systemFont used instead of custom typography extension",
                "suggested_fix": "Use UIFont.dwcaption / .dwbody / project font extensions",
            })

        if _SWIFTUI_SYSTEM_FONT_RE.search(line):
            issues.append({
                "category": "design_system",
                "code": "DS005",
                "severity": "warning",
                "line": line_no,
                "message": "Font.system used instead of custom typography extension",
                "suggested_fix": "Use .h6Headline / .body1 / .subtitle2 / project SwiftUI fonts",
            })

    return issues


def _iter_code_lines(content: str):
    in_block_comment = False
    for idx, raw in enumerate(content.splitlines(), start=1):
        line = raw
        if in_block_comment:
            end = line.find("*/")
            if end == -1:
                continue
            line = line[end + 2 :]
            in_block_comment = False
        start = line.find("/*")
        if start != -1:
            end = line.find("*/", start + 2)
            if end == -1:
                in_block_comment = True
                line = line[:start]
            else:
                line = line[:start] + line[end + 2 :]
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        if not stripped:
            continue
        yield idx, line
