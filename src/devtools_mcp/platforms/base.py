"""Base platform driver — defines the contract all platform drivers implement."""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class BuildError:
    """A single build error with source location."""

    file: str | None
    line: int | None
    column: int | None
    message: str


@dataclass
class BuildResult:
    """Structured result from a build operation."""

    success: bool
    errors: list[BuildError] = field(default_factory=list)
    warnings: list[BuildError] = field(default_factory=list)
    build_log_tail: str = ""

    @staticmethod
    def _short_path(path: str | None) -> str | None:
        """Shorten absolute paths to project-relative for compact output."""
        if not path:
            return path
        # Strip DerivedData paths to just filename
        if "DerivedData" in path:
            return os.path.basename(path)
        # Could add project-specific path stripping here if needed
        return path

    def _grouped_warnings(self) -> list[dict]:
        """Group warnings by message to avoid repetitive output.

        Returns a compact list: one entry per unique message with file count
        and up to 3 example locations.
        """
        groups: dict[str, list[BuildError]] = defaultdict(list)
        for w in self.warnings:
            groups[w.message].append(w)

        result = []
        for msg, items in groups.items():
            locations = [
                f"{self._short_path(w.file)}:{w.line}"
                for w in items[:3]
            ]
            entry: dict = {"message": msg, "count": len(items)}
            if len(items) == 1:
                entry["file"] = self._short_path(items[0].file)
                entry["line"] = items[0].line
            else:
                entry["example_locations"] = locations
                if len(items) > 3:
                    entry["example_locations"].append(f"...and {len(items) - 3} more")
            result.append(entry)
        return result

    def to_dict(self) -> dict:
        """Serialize to dict. Groups warnings to avoid huge MCP responses."""
        return {
            "success": self.success,
            "errors": [
                {
                    "file": self._short_path(e.file),
                    "line": e.line,
                    "column": e.column,
                    "message": e.message,
                }
                for e in self.errors
            ],
            "warnings_grouped": self._grouped_warnings(),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "build_log_tail": self.build_log_tail,
        }


class PlatformDriver(ABC):
    """Base class for platform-specific build/run drivers.

    Subclass this for iOS, Android, Web, etc.
    Each driver knows how to build, run, and list available targets
    for its platform.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform name (e.g., 'iOS', 'Android', 'Web')."""

    @abstractmethod
    def build(self, **kwargs) -> BuildResult:
        """Build the project. Returns structured build result."""

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Build and run the project on a device/emulator/browser."""

    @abstractmethod
    def list_devices(self) -> list[dict]:
        """List available devices/emulators/browsers for this platform."""

    @staticmethod
    def run_cmd(args: list[str], timeout: int = 600) -> tuple[int, str, str]:
        """Run a subprocess and return (returncode, stdout, stderr)."""
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
