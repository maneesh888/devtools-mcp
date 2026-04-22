"""DevTools MCP Server — build, run, and dev workflow tools for full-stack development.

Provides tools that AI agents cannot do natively:
- **Mobile**: xcodebuild/gradle orchestration, simulator/emulator management, IDE automation
- **Web**: Playwright/Cypress testing, build tools, deployment automation
- **Server**: API testing, Docker orchestration, deployment helpers
- **Quality**: Code auditing, design system compliance, hygiene checks

Current status:
  ✅ iOS: Complete (build, run, audit)
  ✅ Android: Complete (build, run, lint, test, audit)
  🚧 Web: Planned (Playwright, build, deploy)
  🚧 Server: Planned (API testing, Docker, SSH deploy)
"""

import json
import os
import shlex
import subprocess
from functools import lru_cache
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .platforms.android import AndroidDriver
from .platforms.ios import IOSDriver
from .audit import audit_changed_files as run_audit
from .xcode_control import (
    _stop_and_dismiss as xc_stop_and_dismiss,
    xcode_run as xc_run,
    xcode_stop as xc_stop,
)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
mcp = FastMCP("devtools-mcp")

# ---------------------------------------------------------------------------
# Platform drivers
# ---------------------------------------------------------------------------
ios = IOSDriver()
android = AndroidDriver()

# ---------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_projects_config() -> dict:
    default = Path(__file__).resolve().parents[2] / "mcp_helper.json"
    config_path = Path(os.environ.get("DEVTOOLS_PROJECTS_CONFIG", default))
    if not config_path.exists():
        return {}
    with config_path.open() as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# iOS Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ios_build(
    project_path: str = "",
    scheme: str = "",
    configuration: str = "",
    simulator: str = "",
    run_after: bool = True,
) -> str:
    """Build the iOS project for Simulator.

    Returns structured JSON with build success/failure, parsed errors
    (with file path, line, column, message), warnings, and build log tail.
    Use the error details to locate and fix issues in source files.

    On success, automatically triggers Cmd+R in Xcode to run the app
    so you can test immediately with full Xcode debugging support.
    Pass `run_after=False` to skip the auto-run.

    Args:
        project_path: Path to .xcodeproj (defaults to env IOS_MCP_PROJECT)
        scheme: Xcode scheme to build (defaults to env IOS_MCP_SCHEME)
        configuration: Build configuration (defaults to env IOS_MCP_CONFIGURATION)
        simulator: Simulator name to target (defaults to env IOS_MCP_SIMULATOR)
        run_after: When True (default), auto-runs the app in Xcode on
                   successful build. Set False for build-only checks.
    """
    kwargs = _strip_empty(
        project_path=project_path,
        scheme=scheme,
        configuration=configuration,
        simulator=simulator,
    )
    result = ios.build(**kwargs)
    result_dict = result.to_dict()

    if result.success and run_after:
        xc_stop_and_dismiss()
        run_result = xc_run()
        result_dict["xcode_run"] = run_result

    return json.dumps(result_dict, indent=2)


@mcp.tool()
def ios_list_simulators() -> str:
    """List all available iOS simulators with name, UDID, state, and OS version."""
    devices = ios.list_devices()
    return json.dumps(devices, indent=2)


# ---------------------------------------------------------------------------
# Android Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def android_build(variant: str = "debug", clean: bool = False) -> str:
    """Build Android app with Gradle.

    Returns structured JSON with build success/failure, parsed errors
    (with file path, line, column, message), warnings, and build log tail.

    Args:
        variant: Build variant (debug/release).
        clean: Run clean before build.
    """
    result = android.build(variant=variant, clean=clean)
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def android_list_emulators() -> str:
    """List available Android emulators (AVDs).

    Returns JSON array of AVDs with name, type, and status.
    """
    emulators = android.list_emulators()
    return json.dumps(emulators, indent=2)


@mcp.tool()
def android_list_devices() -> str:
    """List connected Android devices via adb.

    Returns JSON array of devices with id, type, status, and info.
    """
    devices = android.list_devices()
    return json.dumps(devices, indent=2)


@mcp.tool()
def android_start_emulator(avd_name: str = "") -> str:
    """Start an Android emulator by AVD name.

    Args:
        avd_name: AVD name to boot. Uses DEVTOOLS_ANDROID_EMULATOR if empty.
    """
    name = avd_name if avd_name else None
    success = android.start_emulator(name)
    return json.dumps({"success": success})


@mcp.tool()
def android_install_apk(apk_path: str, device_id: str = "") -> str:
    """Install APK on device/emulator.

    Args:
        apk_path: Path to the .apk file.
        device_id: Target device serial. Uses default if empty.
    """
    did = device_id if device_id else None
    success = android.install_apk(apk_path, did)
    return json.dumps({"success": success})


@mcp.tool()
def android_run_app(
    package_name: str,
    activity_name: str,
    device_id: str = "",
) -> str:
    """Launch Android app on device.

    Args:
        package_name: e.g. "com.example.myapp"
        activity_name: e.g. ".MainActivity"
        device_id: Target device serial. Uses default if empty.
    """
    did = device_id if device_id else None
    success = android.run_app(package_name, activity_name, did)
    return json.dumps({"success": success})


@mcp.tool()
def android_stop_app(package_name: str, device_id: str = "") -> str:
    """Force-stop an Android app.

    Args:
        package_name: e.g. "com.example.myapp"
        device_id: Target device serial. Uses default if empty.
    """
    did = device_id if device_id else None
    success = android.stop_app(package_name, did)
    return json.dumps({"success": success})


@mcp.tool()
def android_test(test_type: str = "unit") -> str:
    """Run Android tests (unit or instrumented).

    Returns JSON with total, passed, failed, skipped counts and failure details.

    Args:
        test_type: "unit" or "instrumented"
    """
    results = android.test(test_type)
    return json.dumps(results, indent=2)


@mcp.tool()
def android_lint() -> str:
    """Run Android Lint checks.

    Returns structured JSON BuildResult with lint errors and warnings.
    """
    result = android.lint()
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def audit_kotlin_hygiene(base_ref: str = "") -> str:
    """Audit Kotlin code for anti-patterns.

    Checks for: println() usage, !! null assertions, TODO/FIXME comments.

    Args:
        base_ref: If set, only audit files changed vs this git ref.
    """
    ref = base_ref if base_ref else None
    issues = android.audit_kotlin_hygiene(ref)
    return json.dumps(issues, indent=2)


# ---------------------------------------------------------------------------
# Pre-Commit Audit
# ---------------------------------------------------------------------------


@mcp.tool()
def audit_changed_files(
    project_path: str,
    checks: list[str] | None = None,
    base_ref: str = "",
    xcstrings_path: str = "",
    paths: list[str] | None = None,
) -> str:
    """Composite audit + parallel build check + LLM-filtered review.

    ENFORCED WORKFLOW (every call, no exceptions):

    1. PARALLEL DISPATCH: in the SAME message that calls this tool, also
       invoke `ios_build(run_after=False)` as a second tool use. Build
       (~30-60s) runs concurrently with audit (~5s) so total wall-time
       = build time, not build + audit.

    2. When both return, review audit findings in code context: read +/-5
       lines around each flagged line, classify REAL / FALSE_POSITIVE /
       NEEDS_HUMAN. See `llm_review_guidance` in the result for FP rules.

    3. Report to user in this order:
       a. Build status (clean / failed, if failed list errors
          with file:line; build errors block commit regardless of audit).
       b. Real audit issues grouped by check, file:line + rationale + fix.
       c. Summary: "Build: ok/failed | X real | Y filtered | Z needs decision"

    NEVER dump raw JSON to the user. Only `paths` / `base_ref` vary between
    invocations, the workflow is identical every time.

    Checks (all run by default):
      - design_system : stock UIColor/Color, raw RGB/hex literals, system
                        fonts that should come from design system
      - file_metadata : flags AI-generated 'Created by' headers
      - swift_hygiene : leftover print(), try!, fatalError(), TODO/FIXME

    Scope selection (in priority order):
      1. `paths` set   -> audit exactly those files/directories
      2. `base_ref` set -> branch scope: all files changed vs the ref
      3. otherwise     -> pre-commit scope: uncommitted + staged changes.

    Args:
        project_path: Root of the iOS project (the git repo).
        checks: Subset of ['design_system','file_metadata','swift_hygiene'].
                None = run all.
        base_ref: Optional git ref to diff against (e.g. 'master').
        xcstrings_path: Override for Localizable.xcstrings location.
        paths: Explicit files or directories to audit.
    """
    result = run_audit(
        project_path=project_path,
        checks=checks,
        base_ref=base_ref or None,
        xcstrings_path=xcstrings_path,
        paths=paths,
    )
    return json.dumps(result, separators=(",", ":"))


@mcp.prompt()
def audit_and_review() -> str:
    """Trigger the full audit + parallel build + LLM review workflow."""
    return """Call `audit_changed_files` with the scope matching the user's ask:

- "pre-commit audit" / "review my changes" -> default (no `paths`, no `base_ref`)
- "audit folder X" / "audit these files Y" -> `paths=[...]`
- "pre-PR audit vs master" -> `base_ref='master'`

The tool's docstring carries the full enforced workflow (parallel build
dispatch + LLM review + report format). Follow it exactly. Do NOT skip
the parallel `ios_build(run_after=False)` dispatch in the same message.
"""


# ---------------------------------------------------------------------------
# Xcode Control Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def xcode_run_app() -> str:
    """Send Cmd+R to Xcode to run the app with full debugging support.

    Stops any currently running session first, then triggers Run.
    Xcode must already be open with the project.
    """
    return json.dumps(xc_run(), indent=2)


@mcp.tool()
def xcode_stop_app() -> str:
    """Send Cmd+. to Xcode to stop the running app.

    Stops the currently running debug session in Xcode.
    """
    return json.dumps(xc_stop(), indent=2)


# ---------------------------------------------------------------------------
# Gateway Management Tools
# ---------------------------------------------------------------------------


def _gateway_cwd() -> Path:
    cfg = _load_projects_config()
    workspace = cfg.get("host_workspace", str(Path.home()))
    return Path(workspace) / "llm-gateway"


def _gateway_log_dir() -> Path:
    cfg = _load_projects_config()
    return Path(cfg.get("log_dir", "/tmp"))


@mcp.tool()
def gateway_build() -> str:
    """Build the LLM gateway (npm install + npm run build).

    Uses host_workspace/llm-gateway from mcp_helper.json.
    Returns JSON with stdout, stderr, exit_code, and success.
    """
    cwd = _gateway_cwd()
    try:
        install = subprocess.run(
            ["npm", "install"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if install.returncode != 0:
            return json.dumps(
                {
                    "stdout": install.stdout,
                    "stderr": install.stderr,
                    "exit_code": install.returncode,
                    "success": False,
                    "stage": "npm install",
                },
                indent=2,
            )

        build = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
        return json.dumps(
            {
                "stdout": build.stdout,
                "stderr": build.stderr,
                "exit_code": build.returncode,
                "success": build.returncode == 0,
                "stage": "npm run build",
            },
            indent=2,
        )
    except subprocess.TimeoutExpired as e:
        return json.dumps({"error": f"Build timed out: {e}", "exit_code": -1, "success": False}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "exit_code": -1, "success": False}, indent=2)


@mcp.tool()
def gateway_start(port: int = 0) -> str:
    """Start the LLM gateway server in the background (npm start).

    Uses host_workspace/llm-gateway from mcp_helper.json.
    Port priority: 1) Function param, 2) GATEWAY_PORT env var, 3) Default 8081
    Returns JSON with pid and status.

    Args:
        port: Port to listen on (default: use GATEWAY_PORT env or 8081).
    """
    env_port = os.environ.get("GATEWAY_PORT")
    if port == 0:
        port = int(env_port) if env_port and env_port.isdigit() else 8081

    cwd = _gateway_cwd()
    try:
        proc_env = {**os.environ, "PORT": str(port)}
        log_path = _gateway_log_dir() / "llm-gateway.log"
        log_fh = open(str(log_path), "w")  # noqa: SIM115
        proc = subprocess.Popen(
            ["npm", "start"],
            cwd=str(cwd),
            env=proc_env,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
        return json.dumps({"pid": proc.pid, "status": "started", "port": port}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "status": "failed"}, indent=2)


@mcp.tool()
def gateway_stop() -> str:
    """Stop the LLM gateway server.

    Kills the process recorded in <log_dir>/llm-gateway.pid if it exists.
    """
    pid_file = _gateway_log_dir() / "llm-gateway.pid"
    try:
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 15)  # SIGTERM
            pid_file.unlink(missing_ok=True)
            return json.dumps({"success": True, "message": f"Stopped gateway (pid {pid})"}, indent=2)
        else:
            return json.dumps({"success": False, "message": "No PID file found, gateway may not be running"}, indent=2)
    except ProcessLookupError:
        pid_file.unlink(missing_ok=True)
        return json.dumps({"success": True, "message": "Process already gone, cleaned up PID file"}, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, indent=2)


# ---------------------------------------------------------------------------
# CI Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_projects() -> str:
    """List available projects and their allowed CI commands.

    Returns JSON with project names and the CI commands registered for each.
    """
    cfg = _load_projects_config()
    projects = cfg.get("projects", {})
    return json.dumps(
        {name: {"ci": info.get("ci", [])} for name, info in projects.items()},
        indent=2,
    )


@mcp.tool()
def run_ci(project_name: str, command: str) -> str:
    """Run a whitelisted CI command for a project.

    The command must be in the project's `ci` list in mcp_helper.json.
    Runs in <host_workspace>/<project_name> with a 300 s timeout.

    Returns JSON with stdout, stderr, and exit_code.

    Args:
        project_name: Key from mcp_helper.json projects (e.g. "llm-gateway").
        command: CI command string exactly as listed (e.g. "npm test").
    """
    cfg = _load_projects_config()
    projects = cfg.get("projects", {})

    if project_name not in projects:
        return json.dumps(
            {"error": f"Unknown project '{project_name}'", "available": list(projects)},
            indent=2,
        )

    allowed = projects[project_name].get("ci", [])
    if command not in allowed:
        return json.dumps(
            {"error": f"Command not whitelisted for '{project_name}'", "allowed": allowed},
            indent=2,
        )

    workspace = cfg.get("host_workspace", str(Path.home()))
    cwd = Path(workspace) / project_name

    try:
        # Use shlex.split for safer execution. The command is validated
        # against the exact whitelist above, so injection risk is minimal,
        # but avoiding shell=True is still best practice.
        proc = subprocess.run(
            shlex.split(command),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
        return json.dumps(
            {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
            },
            indent=2,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out after 300s", "exit_code": -1}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "exit_code": -1}, indent=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_empty(**kwargs) -> dict:
    """Remove empty string values so platform defaults are used.

    Only strips empty strings, not other falsy values like False or 0.
    """
    return {k: v for k, v in kwargs.items() if v != ""}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Run the MCP server (stdio by default, SSE for container-to-host access)."""
    import argparse
    from mcp.server.transport_security import TransportSecuritySettings

    parser = argparse.ArgumentParser(description="DevTools MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7888)
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                "127.0.0.1:*", "localhost:*", "[::1]:*",
                f"host.docker.internal:{args.port}",
                f"localhost:{args.port}",
            ],
            allowed_origins=[
                "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
                f"http://host.docker.internal:{args.port}",
            ],
        )

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
