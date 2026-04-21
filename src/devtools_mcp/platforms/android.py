"""Android platform driver — Gradle build, emulator management, APK installation.

Planned features:
- gradle build orchestration
- AVD/emulator listing and control
- APK/AAB build and installation
- Logcat parsing
- Android Lint integration
"""

from __future__ import annotations

import os
from .base import BuildResult, PlatformDriver

# ---------------------------------------------------------------------------
# Defaults from environment
# ---------------------------------------------------------------------------
DEFAULT_PROJECT = os.getenv("DEVTOOLS_ANDROID_PROJECT", "")
DEFAULT_MODULE = os.getenv("DEVTOOLS_ANDROID_MODULE", "app")
DEFAULT_BUILD_VARIANT = os.getenv("DEVTOOLS_ANDROID_BUILD_VARIANT", "debug")
DEFAULT_EMULATOR = os.getenv("DEVTOOLS_ANDROID_EMULATOR", "")
DEFAULT_SDK_ROOT = os.getenv("DEVTOOLS_ANDROID_SDK_ROOT", os.path.expanduser("~/Library/Android/sdk"))


class AndroidDriver(PlatformDriver):
    """Android platform driver using Gradle and adb."""

    @property
    def platform_name(self) -> str:
        return "Android"

    def build(
        self,
        project_path: str = DEFAULT_PROJECT,
        module: str = DEFAULT_MODULE,
        variant: str = DEFAULT_BUILD_VARIANT,
    ) -> BuildResult:
        """Build the Android project using Gradle.
        
        Args:
            project_path: Path to Android project root (where gradlew lives)
            module: Module to build (default: "app")
            variant: Build variant (debug/release)
        
        Returns:
            BuildResult with success/failure, errors, warnings
        """
        raise NotImplementedError("Android build not yet implemented")

    def list_devices(self) -> list[dict]:
        """List available emulators and connected devices.
        
        Returns:
            List of dicts with name, serial, state
        """
        raise NotImplementedError("Android device listing not yet implemented")

    def install_apk(self, apk_path: str, device_serial: str = "") -> dict:
        """Install APK to device or emulator.
        
        Args:
            apk_path: Path to APK file
            device_serial: Optional device serial (uses default if empty)
        
        Returns:
            Dict with success status and any errors
        """
        raise NotImplementedError("APK installation not yet implemented")
