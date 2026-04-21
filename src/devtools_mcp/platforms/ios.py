"""iOS platform driver — Xcode build, simulator management, app launching."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass

from .base import BuildError, BuildResult, PlatformDriver

# ---------------------------------------------------------------------------
# Defaults from environment
# ---------------------------------------------------------------------------
DEFAULT_PROJECT = os.getenv("DEVTOOLS_IOS_PROJECT", "")
DEFAULT_SCHEME = os.getenv("DEVTOOLS_IOS_SCHEME", "")
DEFAULT_CONFIGURATION = os.getenv("DEVTOOLS_IOS_CONFIGURATION", "Debug")
DEFAULT_SIMULATOR = os.getenv("DEVTOOLS_IOS_SIMULATOR", "iPhone 17 Pro")
DEFAULT_DERIVED_DATA = os.getenv(
    "DEVTOOLS_IOS_DERIVED_DATA",
    str(Path.home() / "Library/Developer/Xcode/DerivedData-MCP")
)

# ---------------------------------------------------------------------------
# Error parsing regexes
# ---------------------------------------------------------------------------
_ERROR_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+error:\s+(?P<msg>.+)$",
    re.MULTILINE,
)
_WARNING_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+warning:\s+(?P<msg>.+)$",
    re.MULTILINE,
)
_LINKER_ERROR_RE = re.compile(
    r"^(?:ld|clang):\s+error:\s+(?P<msg>.+)$",
    re.MULTILINE,
)
_BUILD_ERROR_SUMMARY_RE = re.compile(
    r"^error:\s+(?P<msg>.+)$",
    re.MULTILINE,
)

@dataclass
class TargetDevice:
    udid: str
    name: str
    is_simulator: bool

class IOSDriver(PlatformDriver):
    """iOS platform driver using xcodebuild and simctl."""

    @property
    def platform_name(self) -> str:
        return "iOS"

    def build(
        self,
        project_path: str = DEFAULT_PROJECT,
        scheme: str = DEFAULT_SCHEME,
        configuration: str = DEFAULT_CONFIGURATION,
        simulator: str = "",
    ) -> BuildResult:
        """Build the Xcode project for iOS Simulator or Device."""
        
        target = self._resolve_target(simulator)
        if isinstance(target, dict):
            # Gracefully fail build with the resolution error
            return BuildResult(success=False, errors=[BuildError(file=None, line=None, column=None, message=target["error"])])

        if target.is_simulator:
            destination = f"platform=iOS Simulator,id={target.udid}"
        else:
            destination = f"platform=iOS,id={target.udid}"

        cmd = [
            "xcodebuild",
            "build",
            "-project", project_path,
            "-scheme", scheme,
            "-configuration", configuration,
            "-destination", destination,
            "-derivedDataPath", DEFAULT_DERIVED_DATA,
            "-allowProvisioningUpdates",
            "-skipPackageUpdates",
        ]

        # Note: CODE_SIGNING_ALLOWED must remain YES even for simulators
        # because the app uses App Groups entitlements for Core Data storage.

        rc, stdout, stderr = self.run_cmd(cmd, timeout=600)
        combined = stdout + "\n" + stderr

        errors, warnings = self._parse_build_output(combined)

        # On success, minimal tail. On failure, keep last 50 lines for debugging.
        if rc == 0:
            tail = "BUILD SUCCEEDED"
        else:
            lines = combined.strip().splitlines()
            tail = "\n".join(lines[-50:]) if len(lines) > 50 else combined.strip()

        return BuildResult(
            success=rc == 0,
            errors=errors,
            warnings=warnings,
            build_log_tail=tail,
        )

    def run(
        self,
        project_path: str = DEFAULT_PROJECT,
        scheme: str = DEFAULT_SCHEME,
        configuration: str = DEFAULT_CONFIGURATION,
        simulator: str = "",
    ) -> dict:
        """Build and run the app on iOS Simulator or connected device."""
        steps: list[str] = []

        # Step 1: Active Target Resolution
        target = self._resolve_target(simulator)
        if isinstance(target, dict):
            return target  # Abort safely pointing AI to issue
            
        steps.append(f"Resolved Target: {target.name} ({target.udid}), IsSimulator: {target.is_simulator}")

        # Step 2: Boot if Simulator
        if target.is_simulator:
            booted = self._is_simulator_booted(target.udid)
            if not booted:
                rc_boot, _, stderr_boot = self.run_cmd(["xcrun", "simctl", "boot", target.udid])
                if rc_boot != 0:
                    steps.append(f"Boot failed: {stderr_boot.strip()}")
                else:
                    steps.append(f"Booted {target.name} ({target.udid})")
            else:
                steps.append(f"{target.name} already booted ({target.udid})")

            # Open Simulator app to the specific device so it appears centrally
            self.run_cmd(["open", "-a", "Simulator", "--args", "-CurrentDeviceUDID", target.udid])
            steps.append(f"Opened Simulator.app (focused on {target.name})")

        # Step 3: Build
        build_result = self.build(project_path, scheme, configuration, target.udid)
        if not build_result.success:
            return {
                "success": False,
                "phase": "build",
                "build_result": build_result.to_dict(),
                "steps": steps,
            }
        steps.append("Build succeeded")

        # Step 4: Find .app bundle
        app_path = self._find_app_bundle(scheme, configuration, target.is_simulator)
        if not app_path:
            return {
                "success": False,
                "phase": "locate_app",
                "error": "Could not find .app bundle in DerivedData. Try a clean build.",
                "steps": steps,
            }
        steps.append(f"Found app: {app_path}")

        # Step 5: Install
        if target.is_simulator:
            rc_install, _, stderr_install = self.run_cmd(["xcrun", "simctl", "install", target.udid, app_path])
        else:
            rc_install, _, stderr_install = self.run_cmd(["xcrun", "devicectl", "device", "install", "app", "--device", target.udid, app_path])
            
        if rc_install != 0:
            return {
                "success": False,
                "phase": "install",
                "error": stderr_install.strip(),
                "steps": steps,
            }
        steps.append("Installed app on target")

        # Step 6: Launch
        bundle_id = self._get_bundle_id(app_path)
        if not bundle_id:
            return {
                "success": False,
                "phase": "launch",
                "error": "Could not extract bundle identifier from app.",
                "steps": steps,
            }

        if target.is_simulator:
            rc_launch, _, stderr_launch = self.run_cmd(["xcrun", "simctl", "launch", target.udid, bundle_id])
        else:
            rc_launch, _, stderr_launch = self.run_cmd(["xcrun", "devicectl", "device", "process", "launch", "--device", target.udid, bundle_id])
            
        if rc_launch != 0:
            return {
                "success": False,
                "phase": "launch",
                "error": stderr_launch.strip(),
                "steps": steps,
            }
        steps.append(f"Launched {bundle_id} on {target.name}")

        return {
            "success": True,
            "bundle_id": bundle_id,
            "target": target.name,
            "target_udid": target.udid,
            "app_path": app_path,
            "steps": steps,
        }

    def list_devices(self) -> list[dict]:
        """List available iOS simulators and physical devices."""
        # 1. Simulators
        rc, stdout, _ = self.run_cmd(["xcrun", "simctl", "list", "devices", "available", "-j"])
        sims = []
        if rc == 0:
            data = json.loads(stdout)
            devices = data.get("devices", {})
            for runtime, device_list in sorted(devices.items()):
                os_version = runtime.split("-")[-2:]
                os_ver_str = ".".join(os_version) if len(os_version) == 2 else runtime.split(".")[-1]
                for device in device_list:
                    sims.append({
                        "name": device["name"],
                        "udid": device["udid"],
                        "state": device["state"],
                        "os_version": f"iOS {os_ver_str}",
                        "is_simulator": True
                    })
        
        # 2. Physical Devices via devicectl
        devices = []
        rc_dev, stdout_dev, _ = self.run_cmd(["xcrun", "devicectl", "list", "devices", "-j", "/tmp/devicectl_out.json"])
        if rc_dev == 0 and os.path.exists("/tmp/devicectl_out.json"):
            try:
                with open("/tmp/devicectl_out.json", "r") as f:
                    dev_data = json.load(f)
                    if "result" in dev_data and "devices" in dev_data["result"]:
                        for d in dev_data["result"]["devices"]:
                            tunnel = d.get("connectionProperties", {}).get("tunnelState", "unavailable")
                            state_mapped = "Connected" if tunnel in ["connected", "available", "wired"] else "Disconnected"
                            devices.append({
                                "name": d.get("deviceProperties", {}).get("name", "Unknown"),
                                "udid": d.get("hardwareProperties", {}).get("udid", "Unknown"),
                                "state": state_mapped,
                                "os_version": d.get("deviceProperties", {}).get("osVersionNumber", "Unknown"),
                                "is_simulator": False
                            })
            except Exception:
                pass
                
        return sims + devices

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _resolve_target(self, requested: str) -> TargetDevice | dict:
        """Resolve the build/run target device.

        Priority order:
        1. Explicitly requested name or UDID
        2. Booted simulator matching DEFAULT_SIMULATOR
        3. Any booted simulator
        4. DEFAULT_SIMULATOR even if shutdown (builds don't need it booted)
        5. Error with helpful message
        """
        all_devs = self.list_devices()
        booted_sims = [d for d in all_devs if d["is_simulator"] and d["state"] == "Booted"]
        all_sims = [d for d in all_devs if d["is_simulator"]]

        # 1. Explicitly requested by name or UDID
        if requested:
            for d in all_devs:
                if d["udid"] == requested or d["name"] == requested:
                    return TargetDevice(udid=d["udid"], name=d["name"], is_simulator=d["is_simulator"])
            return {"success": False, "error": f"Requested target '{requested}' not found. List devices to see available ones."}

        # 2. Prefer booted default simulator
        for d in booted_sims:
            if d["name"] == DEFAULT_SIMULATOR:
                return TargetDevice(udid=d["udid"], name=d["name"], is_simulator=d["is_simulator"])

        # 3. Any booted simulator
        if booted_sims:
            d = booted_sims[0]
            return TargetDevice(udid=d["udid"], name=d["name"], is_simulator=d["is_simulator"])

        # 4. Default simulator even if shutdown — xcodebuild only needs the UDID
        for d in all_sims:
            if d["name"] == DEFAULT_SIMULATOR:
                return TargetDevice(udid=d["udid"], name=d["name"], is_simulator=d["is_simulator"])

        # 5. No suitable target found
        return {"success": False, "error": f"Simulator '{DEFAULT_SIMULATOR}' not found. List devices to see available ones."}

    @staticmethod
    def _parse_build_output(output: str) -> tuple[list[BuildError], list[BuildError]]:
        """Parse xcodebuild output into errors and warnings."""
        errors: list[BuildError] = []
        seen_messages: set[str] = set()

        for m in _ERROR_RE.finditer(output):
            errors.append(BuildError(
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("col")),
                message=m.group("msg"),
            ))
            seen_messages.add(m.group("msg"))

        for m in _LINKER_ERROR_RE.finditer(output):
            msg = f"Linker error: {m.group('msg')}"
            if msg not in seen_messages:
                errors.append(BuildError(file=None, line=None, column=None, message=msg))
                seen_messages.add(msg)

        for m in _BUILD_ERROR_SUMMARY_RE.finditer(output):
            msg = m.group("msg")
            if msg not in seen_messages:
                errors.append(BuildError(file=None, line=None, column=None, message=msg))
                seen_messages.add(msg)

        warnings: list[BuildError] = []
        seen_warnings: set[tuple] = set()
        for m in _WARNING_RE.finditer(output):
            # Deduplicate by (file, line, message) — case-insensitive message
            dedup_key = (m.group("file"), m.group("line"), m.group("msg").lower())
            if dedup_key not in seen_warnings:
                seen_warnings.add(dedup_key)
                warnings.append(BuildError(
                    file=m.group("file"),
                    line=int(m.group("line")),
                    column=int(m.group("col")),
                    message=m.group("msg"),
                ))

        return errors, warnings

    def _is_simulator_booted(self, udid: str) -> bool:
        """Check if a simulator is currently booted."""
        all_devs = self.list_devices()
        return any(d["udid"] == udid and d["state"] == "Booted" for d in all_devs)

    @staticmethod
    def _find_app_bundle(scheme: str, configuration: str, is_simulator: bool) -> str | None:
        """Find the built .app in MCP DerivedData based on simulator vs. device directory."""
        derived = Path(DEFAULT_DERIVED_DATA)
        if not derived.exists():
            return None

        search_suffix = "simulator" if is_simulator else "iphoneos"

        products = derived / "Build" / "Products"
        if products.exists():
            for config_dir in products.iterdir():
                if (
                    configuration.lower() in config_dir.name.lower()
                    and search_suffix in config_dir.name.lower()
                ):
                    for app in config_dir.glob("*.app"):
                        return str(app)
        return None

    @staticmethod
    def _get_bundle_id(app_path: str) -> str | None:
        """Extract CFBundleIdentifier from an app's Info.plist."""
        plist = Path(app_path) / "Info.plist"
        if not plist.exists():
            return None
        proc = subprocess.run(
            ["/usr/libexec/PlistBuddy", "-c", "Print :CFBundleIdentifier", str(plist)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
        return None
