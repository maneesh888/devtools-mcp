"""Android platform driver — Gradle build, emulator management, APK installation.

Features:
- Gradle build orchestration with structured error parsing
- AVD/emulator listing and control
- APK installation and app lifecycle management
- Unit and instrumented test execution with JUnit XML parsing
- Android Lint integration
- Kotlin hygiene auditing (println, !!, TODO)
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from .base import BuildError, BuildResult, PlatformDriver

# ---------------------------------------------------------------------------
# Defaults from environment
# ---------------------------------------------------------------------------
DEFAULT_PROJECT = os.getenv("DEVTOOLS_ANDROID_PROJECT", "")
DEFAULT_MODULE = os.getenv("DEVTOOLS_ANDROID_MODULE", "app")
DEFAULT_BUILD_VARIANT = os.getenv("DEVTOOLS_ANDROID_BUILD_VARIANT", "debug")
DEFAULT_EMULATOR = os.getenv("DEVTOOLS_ANDROID_EMULATOR", "")
DEFAULT_SDK_ROOT = os.getenv(
    "DEVTOOLS_ANDROID_SDK_ROOT",
    os.path.expanduser("~/Library/Android/sdk"),
)

# ---------------------------------------------------------------------------
# Error parsing regexes
# ---------------------------------------------------------------------------

# Kotlin compile error: e: file:///path/File.kt:42:10 Unresolved reference: foo
_KOTLIN_ERROR_RE = re.compile(
    r"e: file://(?P<file>.+?):(?P<line>\d+):(?P<col>\d+) (?P<msg>.+)"
)

# Java compile error: /path/File.java:42: error: something went wrong
_JAVA_ERROR_RE = re.compile(
    r"(?P<file>.+?\.java):(?P<line>\d+): error: (?P<msg>.+)"
)

# Resource error: error: resource drawable/icon not found
_RESOURCE_ERROR_RE = re.compile(
    r"error: resource (?P<resource>.+?) not found"
)

# Gradle task failure reason
_FAILURE_REASON_RE = re.compile(
    r"\* What went wrong:\n(.+)", re.MULTILINE
)

# Warning patterns
_KOTLIN_WARNING_RE = re.compile(
    r"w: file://(?P<file>.+?):(?P<line>\d+):(?P<col>\d+) (?P<msg>.+)"
)
_JAVA_WARNING_RE = re.compile(
    r"(?P<file>.+?\.java):(?P<line>\d+): warning: (?P<msg>.+)"
)


class AndroidDriver(PlatformDriver):
    """Android platform driver using Gradle and adb."""

    def __init__(
        self,
        project_path: Optional[str] = None,
        module: Optional[str] = None,
        avd_name: Optional[str] = None,
    ):
        self.project_path = Path(
            project_path or DEFAULT_PROJECT or "."
        )
        self.module = module or DEFAULT_MODULE
        self.avd_name = avd_name or DEFAULT_EMULATOR

    @property
    def platform_name(self) -> str:
        return "Android"

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        variant: str = DEFAULT_BUILD_VARIANT,
        clean: bool = False,
        **kwargs,
    ) -> BuildResult:
        """Build Android app with Gradle.

        Args:
            variant: Build variant (debug/release).
            clean: Run clean before build.

        Returns:
            BuildResult with errors and warnings.
        """
        gradlew = str(self.project_path / "gradlew")
        cmd = [gradlew]
        if clean:
            cmd.append("clean")
        cmd.append(f"{self.module}:assemble{variant.capitalize()}")

        rc, stdout, stderr = self.run_cmd(cmd, timeout=600, cwd=str(self.project_path))
        combined = stdout + "\n" + stderr

        errors = self._parse_gradle_errors(combined)
        warnings = self._parse_gradle_warnings(combined)

        if rc == 0:
            tail = "BUILD SUCCESSFUL"
        else:
            lines = combined.strip().splitlines()
            tail = "\n".join(lines[-50:]) if len(lines) > 50 else combined.strip()

        return BuildResult(
            success=(rc == 0),
            errors=errors,
            warnings=warnings,
            build_log_tail=tail,
        )

    # ------------------------------------------------------------------
    # Device / Emulator management
    # ------------------------------------------------------------------

    def list_emulators(self) -> list[dict]:
        """List available AVDs."""
        rc, stdout, stderr = self.run_cmd(["emulator", "-list-avds"])
        if rc != 0:
            return []

        avds = []
        for line in stdout.strip().split("\n"):
            name = line.strip()
            if name:
                avds.append({
                    "name": name,
                    "type": "emulator",
                    "status": "available",
                })
        return avds

    def list_devices(self) -> list[dict]:
        """List connected Android devices via adb."""
        rc, stdout, stderr = self.run_cmd(["adb", "devices", "-l"])
        if rc != 0:
            return []

        devices = []
        pattern = re.compile(r"(\S+)\s+device\s+(.+)")
        for match in pattern.finditer(stdout):
            device_id = match.group(1)
            info = match.group(2)
            devices.append({
                "id": device_id,
                "type": "emulator" if device_id.startswith("emulator") else "device",
                "status": "connected",
                "info": info,
            })
        return devices

    def start_emulator(self, avd_name: Optional[str] = None) -> bool:
        """Start an Android emulator.

        Args:
            avd_name: AVD name to start. Falls back to self.avd_name.

        Returns:
            True if emulator booted successfully.
        """
        avd = avd_name or self.avd_name
        if not avd:
            raise ValueError("No AVD name specified")

        # Start emulator in background
        subprocess.Popen(
            ["emulator", "-avd", avd, "-no-snapshot-load"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for boot animation to stop (up to 60s)
        for _ in range(60):
            rc, stdout, _ = self.run_cmd(
                ["adb", "shell", "getprop", "init.svc.bootanim"]
            )
            if rc == 0 and "stopped" in stdout:
                return True
            time.sleep(1)

        return False

    # ------------------------------------------------------------------
    # App control
    # ------------------------------------------------------------------

    def install_apk(
        self,
        apk_path: str,
        device_id: Optional[str] = None,
    ) -> bool:
        """Install APK on device/emulator.

        Args:
            apk_path: Path to the .apk file.
            device_id: Target device serial. Uses default if omitted.

        Returns:
            True if installation succeeded.
        """
        cmd = ["adb"]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["install", "-r", apk_path])

        rc, stdout, stderr = self.run_cmd(cmd, timeout=120)
        return rc == 0 and "Success" in stdout

    def run_app(
        self,
        package_name: str,
        activity_name: str,
        device_id: Optional[str] = None,
    ) -> bool:
        """Launch app on device.

        Args:
            package_name: e.g. "com.example.myapp"
            activity_name: e.g. ".MainActivity"
            device_id: Target device serial.

        Returns:
            True if launch succeeded.
        """
        cmd = ["adb"]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend([
            "shell", "am", "start",
            "-n", f"{package_name}/{activity_name}",
        ])

        rc, stdout, stderr = self.run_cmd(cmd)
        return rc == 0

    def run(self, **kwargs) -> dict:
        """Build and run the app. Delegates to build() + run_app()."""
        variant = kwargs.get("variant", DEFAULT_BUILD_VARIANT)
        package_name = kwargs.get("package_name", "")
        activity_name = kwargs.get("activity_name", "")
        device_id = kwargs.get("device_id", None)

        build_result = self.build(variant=variant)
        if not build_result.success:
            return {
                "success": False,
                "phase": "build",
                "build_result": build_result.to_dict(),
            }

        if package_name and activity_name:
            launched = self.run_app(package_name, activity_name, device_id)
            return {
                "success": launched,
                "phase": "launch" if not launched else "complete",
            }

        return {
            "success": True,
            "phase": "build_only",
            "message": "Build succeeded. Provide package_name and activity_name to launch.",
        }

    def stop_app(
        self,
        package_name: str,
        device_id: Optional[str] = None,
    ) -> bool:
        """Force-stop app.

        Args:
            package_name: e.g. "com.example.myapp"
            device_id: Target device serial.

        Returns:
            True if stop succeeded.
        """
        cmd = ["adb"]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["shell", "am", "force-stop", package_name])

        rc, _, _ = self.run_cmd(cmd)
        return rc == 0

    # ------------------------------------------------------------------
    # Testing
    # ------------------------------------------------------------------

    def test(self, test_type: str = "unit") -> dict:
        """Run Android tests.

        Args:
            test_type: "unit" or "instrumented"

        Returns:
            Dict with total, passed, failed, success, and failure details.
        """
        if test_type == "unit":
            task = f"{self.module}:testDebugUnitTest"
        elif test_type == "instrumented":
            task = f"{self.module}:connectedDebugAndroidTest"
        else:
            raise ValueError(f"Unknown test type: {test_type}")

        gradlew = str(self.project_path / "gradlew")
        cmd = [gradlew, task]
        rc, stdout, stderr = self.run_cmd(cmd, timeout=600)

        results = self._parse_test_results()
        results["gradle_rc"] = rc
        return results

    def _parse_test_results(self) -> dict:
        """Parse JUnit XML test reports from build/test-results/."""
        test_dir = self.project_path / self.module / "build" / "test-results"

        total = 0
        passed = 0
        failed = 0
        skipped = 0
        failures: list[dict] = []

        if test_dir.exists():
            for xml_file in test_dir.rglob("*.xml"):
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()

                    suite_tests = int(root.get("tests", 0))
                    suite_failures = int(root.get("failures", 0))
                    suite_errors = int(root.get("errors", 0))
                    suite_skipped = int(root.get("skipped", 0))

                    total += suite_tests
                    failed += suite_failures + suite_errors
                    skipped += suite_skipped

                    for testcase in root.findall(".//testcase"):
                        failure = testcase.find("failure")
                        error = testcase.find("error")
                        fail_elem = failure if failure is not None else error
                        if fail_elem is not None:
                            failures.append({
                                "test": testcase.get("name"),
                                "class": testcase.get("classname"),
                                "message": fail_elem.get("message", ""),
                            })
                except ET.ParseError:
                    continue

        passed = total - failed - skipped

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success": failed == 0,
            "failures": failures,
        }

    # ------------------------------------------------------------------
    # Code quality
    # ------------------------------------------------------------------

    def lint(self) -> BuildResult:
        """Run Android Lint checks.

        Returns:
            BuildResult with lint errors and warnings.
        """
        gradlew = str(self.project_path / "gradlew")
        cmd = [gradlew, f"{self.module}:lint"]
        rc, stdout, stderr = self.run_cmd(cmd, timeout=300)

        lint_report = (
            self.project_path
            / self.module
            / "build"
            / "reports"
            / "lint-results.xml"
        )

        errors: list[BuildError] = []
        warnings: list[BuildError] = []

        if lint_report.exists():
            try:
                tree = ET.parse(lint_report)
                for issue in tree.findall(".//issue"):
                    severity = issue.get("severity", "")
                    location = issue.find("location")

                    be = BuildError(
                        file=location.get("file") if location is not None else None,
                        line=int(location.get("line", 0)) or None if location is not None else None,
                        column=int(location.get("column", 0)) or None if location is not None else None,
                        message=issue.get("message", ""),
                    )

                    if severity in ("Error", "Fatal"):
                        errors.append(be)
                    else:
                        warnings.append(be)
            except ET.ParseError:
                errors.append(BuildError(
                    file=None, line=None, column=None,
                    message="Failed to parse lint-results.xml",
                ))

        return BuildResult(
            success=(rc == 0 and len(errors) == 0),
            errors=errors,
            warnings=warnings,
        )

    def audit_kotlin_hygiene(
        self,
        base_ref: Optional[str] = None,
    ) -> list[dict]:
        """Check Kotlin files for common anti-patterns.

        Checks:
          KH001: println() usage (use Timber/Log instead)
          KH002: !! null assertion (use ?. or ?: instead)
          KH003: TODO/FIXME comments

        Args:
            base_ref: If set, only audit files changed vs this git ref.

        Returns:
            List of issue dicts with file, line, severity, code, message, suggested_fix.
        """
        issues: list[dict] = []

        if base_ref:
            rc, stdout, _ = self.run_cmd(
                ["git", "diff", "--name-only", base_ref],
            )
            files = [
                self.project_path / f
                for f in stdout.strip().split("\n")
                if f.strip().endswith(".kt")
            ]
        else:
            files = list(self.project_path.rglob("*.kt"))

        for file_path in files:
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()

                # Skip comments
                if stripped.startswith("//") or stripped.startswith("/*"):
                    continue

                if "println(" in line:
                    issues.append({
                        "file": str(file_path),
                        "line": line_num,
                        "severity": "warning",
                        "code": "KH001",
                        "message": "println() found - use proper logging (Timber/Logcat)",
                        "suggested_fix": "Replace with Log.d() or remove",
                    })

                if "!!" in line:
                    issues.append({
                        "file": str(file_path),
                        "line": line_num,
                        "severity": "warning",
                        "code": "KH002",
                        "message": "!! null assertion operator - use safe call (?.) or let",
                        "suggested_fix": "Replace !! with ?. or ?: default",
                    })

                if re.search(r"\bTODO\b", line, re.IGNORECASE) or re.search(
                    r"\bFIXME\b", line, re.IGNORECASE
                ):
                    issues.append({
                        "file": str(file_path),
                        "line": line_num,
                        "severity": "info",
                        "code": "KH003",
                        "message": "TODO/FIXME comment found",
                        "suggested_fix": "Create issue or complete task",
                    })

        return issues

    # ------------------------------------------------------------------
    # Error parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_gradle_errors(log: str) -> list[BuildError]:
        """Parse Gradle build output for errors."""
        errors: list[BuildError] = []
        seen: set[str] = set()

        # Kotlin compile errors
        for m in _KOTLIN_ERROR_RE.finditer(log):
            key = f"{m.group('file')}:{m.group('line')}:{m.group('msg')}"
            if key not in seen:
                seen.add(key)
                errors.append(BuildError(
                    file=m.group("file"),
                    line=int(m.group("line")),
                    column=int(m.group("col")),
                    message=m.group("msg"),
                ))

        # Java compile errors
        for m in _JAVA_ERROR_RE.finditer(log):
            key = f"{m.group('file')}:{m.group('line')}:{m.group('msg')}"
            if key not in seen:
                seen.add(key)
                errors.append(BuildError(
                    file=m.group("file"),
                    line=int(m.group("line")),
                    column=None,
                    message=m.group("msg"),
                ))

        # Resource errors
        for m in _RESOURCE_ERROR_RE.finditer(log):
            msg = f"Resource not found: {m.group('resource')}"
            if msg not in seen:
                seen.add(msg)
                errors.append(BuildError(
                    file=None, line=None, column=None,
                    message=msg,
                ))

        # BUILD FAILED with reason
        if "BUILD FAILED" in log:
            fm = _FAILURE_REASON_RE.search(log)
            if fm:
                msg = fm.group(1).strip()
                if msg not in seen:
                    seen.add(msg)
                    errors.append(BuildError(
                        file=None, line=None, column=None,
                        message=msg,
                    ))

        return errors

    @staticmethod
    def _parse_gradle_warnings(log: str) -> list[BuildError]:
        """Parse Gradle build output for warnings."""
        warnings: list[BuildError] = []
        seen: set[tuple] = set()

        for m in _KOTLIN_WARNING_RE.finditer(log):
            key = (m.group("file"), m.group("line"), m.group("msg").lower())
            if key not in seen:
                seen.add(key)
                warnings.append(BuildError(
                    file=m.group("file"),
                    line=int(m.group("line")),
                    column=int(m.group("col")),
                    message=m.group("msg"),
                ))

        for m in _JAVA_WARNING_RE.finditer(log):
            key = (m.group("file"), m.group("line"), m.group("msg").lower())
            if key not in seen:
                seen.add(key)
                warnings.append(BuildError(
                    file=m.group("file"),
                    line=int(m.group("line")),
                    column=None,
                    message=m.group("msg"),
                ))

        return warnings
