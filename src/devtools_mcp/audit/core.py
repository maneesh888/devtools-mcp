"""Orchestrator for composite pre-commit audit."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .design_system_audit import audit_design_system
from .file_metadata_audit import audit_file_metadata
from .localization_audit import audit_localization
from .swift_hygiene_audit import audit_swift_hygiene

ALL_CHECKS = ("localization", "design_system", "file_metadata", "swift_hygiene")

_AUDITABLE_EXTENSIONS = (".swift", ".m", ".mm")

# Directories that contain build artifacts or vendor code — never auditable.
_SKIP_DIRS = {
    ".git", "Pods", "DerivedData", ".build", "build",
    ".swiftpm", "xcuserdata", "Carthage", "fastlane",
}


def get_changed_files(project_path: str, base_ref: str | None = None) -> list[str]:
    """Return Swift/ObjC files with uncommitted, staged, or branch-level changes.

    When base_ref is None, returns files with uncommitted + staged changes
    (pre-commit scope). When base_ref is set (e.g. "master"), returns all
    files changed in the branch relative to that ref.
    """
    if not os.path.isdir(project_path):
        raise NotADirectoryError(f"Project directory not found: {project_path}")

    files: set[str] = set()

    if base_ref:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            files.update(proc.stdout.strip().splitlines())
    else:
        for args in (
            ["git", "diff", "--name-only"],
            ["git", "diff", "--cached", "--name-only"],
        ):
            proc = subprocess.run(
                args,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0:
                files.update(proc.stdout.strip().splitlines())

    auditable = [
        os.path.join(project_path, f)
        for f in sorted(files)
        if f.endswith(_AUDITABLE_EXTENSIONS)
    ]
    return [f for f in auditable if os.path.isfile(f)]


def resolve_paths(project_path: str, paths: list[str]) -> list[str]:
    """Expand a list of files/directories into auditable Swift/ObjC files.

    Relative paths are resolved against project_path. Directories are
    walked recursively, skipping build and vendor directories. Non-
    auditable extensions are dropped silently.
    """
    results: set[str] = set()
    for raw in paths:
        if not raw:
            continue
        candidate = raw if os.path.isabs(raw) else os.path.join(project_path, raw)
        candidate = os.path.abspath(candidate)

        if os.path.isfile(candidate):
            if candidate.endswith(_AUDITABLE_EXTENSIONS):
                results.add(candidate)
        elif os.path.isdir(candidate):
            for root, dirs, files in os.walk(candidate):
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
                for name in files:
                    if name.endswith(_AUDITABLE_EXTENSIONS):
                        results.add(os.path.join(root, name))
    return sorted(results)


def audit_changed_files(
    project_path: str,
    checks: list[str] | None = None,
    base_ref: str | None = None,
    xcstrings_path: str = "",
    paths: list[str] | None = None,
) -> dict:
    """Run a composite audit on Swift/ObjC files.

    Scope selection:
      - `paths` set  -> audit exactly those files/directories (recursive).
      - `base_ref` set -> branch scope (files changed vs the ref).
      - otherwise    -> pre-commit scope (uncommitted + staged changes).

    Returns a structured report with issues grouped per file and summary
    counts by severity. Each check is independent — failure in one does
    not abort the others.
    """
    if not project_path:
        return {"error": "project_path is required"}

    checks = list(checks) if checks else list(ALL_CHECKS)
    invalid = [c for c in checks if c not in ALL_CHECKS]
    if invalid:
        return {
            "error": f"Unknown check(s): {invalid}. Valid: {list(ALL_CHECKS)}",
        }

    if paths:
        files = resolve_paths(project_path, paths)
        scope = "explicit_paths"
    else:
        try:
            files = get_changed_files(project_path, base_ref=base_ref)
        except NotADirectoryError as exc:
            return {"error": str(exc)}
        scope = f"branch:{base_ref}" if base_ref else "uncommitted"

    if not files:
        return {
            "status": "clean",
            "message": "No Swift/ObjC files in audit scope.",
            "checks_run": checks,
            "scope": scope,
            "files_audited": 0,
            "total_issues": 0,
            "by_severity": {"error": 0, "warning": 0, "info": 0},
            "files": [],
        }

    per_file: list[dict] = []
    totals = {"error": 0, "warning": 0, "info": 0}

    for file_path in files:
        issues: list[dict] = []
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            per_file.append({
                "file": _rel(file_path, project_path),
                "error": f"Could not read file: {exc}",
                "issues": [],
            })
            continue

        if "localization" in checks:
            issues.extend(
                audit_localization(file_path, content, xcstrings_path=xcstrings_path)
            )
        if "design_system" in checks:
            issues.extend(audit_design_system(file_path, content))
        if "file_metadata" in checks:
            issues.extend(audit_file_metadata(file_path, content))
        if "swift_hygiene" in checks:
            issues.extend(audit_swift_hygiene(file_path, content))

        issues.sort(key=lambda i: (i.get("line", 0), i.get("code", "")))

        for issue in issues:
            sev = issue.get("severity", "info")
            if sev in totals:
                totals[sev] += 1

        per_file.append({
            "file": _rel(file_path, project_path),
            "issue_count": len(issues),
            "issues": issues,
        })

    total_issues = sum(totals.values())

    return {
        "status": "clean" if total_issues == 0 else "issues_found",
        "checks_run": checks,
        "scope": scope,
        "files_audited": len(files),
        "total_issues": total_issues,
        "by_severity": totals,
        "files": per_file,
        "llm_review_required": total_issues > 0,
        "llm_review_guidance": (
            "RAW pattern-matched findings — expect 50-80% false positives in "
            "LOCALIZATION and DESIGN_SYSTEM categories. Common FPs there: "
            "enum raw values, API/JSON keys, log/debug strings, data-mapping "
            "dictionaries, already-localized (&&\"...\" or NSLocalizedString), "
            "constants used for comparison. SWIFT_HYGIENE findings (print, "
            "try!, fatalError, TODO/FIXME) are almost always REAL — do NOT "
            "filter them out. For EACH finding: read ±5 lines of file "
            "context, then classify REAL / FALSE_POSITIVE / NEEDS_HUMAN. "
            "Report to user in this order: (a) parallel `ios_build` status "
            "(✅/❌) — if failed, list build errors FIRST, they block commit; "
            "(b) real audit issues grouped by check type, file:line + "
            "rationale + fix. End with: 'Build: ok/failed | X real | Y "
            "filtered | Z needs decision'. DO NOT dump raw findings."
        ),
    }


def _rel(path: str, base: str) -> str:
    try:
        return os.path.relpath(path, base)
    except ValueError:
        return path
