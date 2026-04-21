"""DevTools MCP Server — build, run, and dev workflow tools for full-stack development.

Provides tools that AI agents cannot do natively:
- **Mobile**: xcodebuild/gradle orchestration, simulator/emulator management, IDE automation
- **Web**: Playwright/Cypress testing, build tools, deployment automation
- **Server**: API testing, Docker orchestration, deployment helpers
- **Quality**: Code auditing, design system compliance, hygiene checks

Current status:
  ✅ iOS: Complete (build, run, audit, demo)
  🚧 Android: Planned (gradle, emulator, APK)
  🚧 Web: Planned (Playwright, build, deploy)
  🚧 Server: Planned (API testing, Docker, SSH deploy)
"""

import json

from mcp.server.fastmcp import FastMCP

from .platforms.ios import IOSDriver
from .audit import audit_changed_files as run_audit
# Localization tools available but not exposed yet
# from .localization import (
#     add_key as loc_add_key,
#     check_key as loc_check_key,
#     execute_migration as loc_execute_migration,
#     read_xcstrings as loc_read_xcstrings,
#     remove_old_key as loc_remove_old_key,
#     search_keys as loc_search_keys,
# )
# from .localization.xcstrings import is_old_format as loc_is_old_format
from .demo import switch_launch_vc, get_current_target, VALID_TARGETS
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

# Future platform drivers:
# android = AndroidDriver()
# web = WebDriver()
# server = ServerDriver()

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
    Pass `run_after=False` to skip the auto-run — useful as a parallel
    build-check alongside an audit without disrupting the simulator.

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

    # On successful build (unless suppressed), stop any running app then Cmd+R in Xcode
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

    ENFORCED WORKFLOW (every call — no exceptions):

    1. PARALLEL DISPATCH — in the SAME message that calls this tool, also
       invoke `ios_build(run_after=False)` as a second tool use. Build
       (~30-60s) runs concurrently with audit (~5s) so total wall-time
       ≈ build time, not build + audit.

    2. When both return, review audit findings in code context: read ±5
       lines around each flagged line, classify REAL / FALSE_POSITIVE /
       NEEDS_HUMAN. See `llm_review_guidance` in the result for FP rules.

    3. Report to user in this order:
       a. Build status (✅ clean / ❌ failed — if failed, list errors
          with file:line; build errors block commit regardless of audit).
       b. Real audit issues grouped by check, file:line + rationale + fix.
       c. Summary: "Build: ok/failed | X real | Y filtered | Z needs decision"

    NEVER dump raw JSON to the user. Only `paths` / `base_ref` vary between
    invocations — the workflow is identical every time.

    Single entry point for any "pre-commit audit", "pre-push audit",
    "review my changes", or "audit this directory / these files" request.

    Checks (all run by default):
      - design_system : stock UIColor/Color, raw RGB/hex literals, system
                        fonts that should come from design system
      - file_metadata : flags AI-generated 'Created by' headers
      - swift_hygiene : leftover print(), try!, fatalError(), TODO/FIXME

    Scope selection (in priority order):
      1. `paths` set   -> audit exactly those files/directories
                          (directories walked recursively; build dirs skipped).
                          Use this for "audit this folder" or "audit these files".
      2. `base_ref` set -> branch scope: all files changed vs the ref
                           (e.g. base_ref='master' for pre-PR review).
      3. otherwise     -> pre-commit scope: uncommitted + staged changes.

    Args:
        project_path: Root of the iOS project (the git repo).
        checks: Subset of ['design_system','file_metadata','swift_hygiene'].
                None = run all.
        base_ref: Optional git ref to diff against (e.g. 'master').
                  Ignored when `paths` is provided.
        xcstrings_path: Override for Localizable.xcstrings location (if using localization audit).
        paths: Explicit files or directories to audit (absolute or relative
               to project_path). When set, overrides git-based scoping.
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

- "pre-commit audit" / "review my changes" → default (no `paths`, no `base_ref`)
- "audit folder X" / "audit these files Y" → `paths=[...]`
- "pre-PR audit vs master" → `base_ref='master'`

The tool's docstring carries the full enforced workflow (parallel build
dispatch + LLM review + report format). Follow it exactly — do NOT skip
the parallel `ios_build(run_after=False)` dispatch in the same message.
"""


# ---------------------------------------------------------------------------
# Demo / VC Switcher Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def demo_set_launch_vc(target: str) -> str:
    """Switch which view controller launches in the iOS app.

    Rewrites AppFlow.swift's setLaunchScreen method to show the chosen VC.
    Use this before a demo to quickly swap screens without manual code edits.

    Valid targets depend on your project's AppFlow.swift configuration.
    Common examples:
      - normal    : production flow
      - textfield : CustomTextFieldTableViewController
      - baseform  : FormVCDemoViewController (UIKit)
      - swiftuiform : SwiftUIFormDemoView (SwiftUI)
      - tabs      : UITabBarController with test VCs

    Args:
        target: Target name (must match your AppFlow.swift targets).
    """
    result = switch_launch_vc(target)
    return json.dumps(result, indent=2)


@mcp.tool()
def demo_get_launch_vc() -> str:
    """Check which demo view controller is currently set in AppFlow.swift.

    Returns the active target name and list of valid targets.
    """
    result = get_current_target()
    return json.dumps(result, indent=2)


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
