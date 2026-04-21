"""Demo VC switcher for AppFlow.swift.

Rewrites the `setLaunchScreen` method body to point at a chosen
view controller target, keeping all the helper methods intact.
"""

import os
import re
from pathlib import Path

# Configure via environment variable (relative to project root or absolute)
APPFLOW_PATH = os.getenv("DEVTOOLS_IOS_APPFLOW_PATH", "")

# The VC assignment lines for each target.
# "normal" restores the production flow.
_TARGETS: dict[str, str] = {
    "normal": (
        "        referenceController = viewcontrollerFlowManager"
        ".launchScreenController(skipWalktrhough: skipWalktrhough, action: action)"
    ),
    "textfield": (
        "        referenceController = showTextFieldViewController()"
    ),
    "baseform": (
        "        referenceController = showBaseFormViewController()"
    ),
    "swiftuiform": (
        "        referenceController = showReusableFormViewController()"
    ),
    "tabs": (
        "        referenceController = showTabControllerForTesting()"
        " // 📱 Test all 3 form implementations in tabs"
    ),
}

VALID_TARGETS = list(_TARGETS.keys())

# Regex that matches the entire setLaunchScreen method body
# from its signature up to (but not including) the next `func ` at the same indent.
_METHOD_RE = re.compile(
    r"(    func setLaunchScreen\(skipWalktrhough: Bool, action: Action\? = nil\) \{)"
    r"(.*?)"
    r"(\n    \})",
    re.DOTALL,
)


def switch_launch_vc(target: str) -> dict:
    """Rewrite setLaunchScreen to launch the given target VC.

    Args:
        target: One of 'normal', 'textfield', 'baseform', 'swiftuiform', 'tabs'.

    Returns:
        Dict with success status, target set, and any error.
    """
    target = target.strip().lower()

    if target not in _TARGETS:
        return {
            "success": False,
            "error": f"Unknown target '{target}'. Valid targets: {VALID_TARGETS}",
        }

    path = Path(APPFLOW_PATH)
    if not path.exists():
        return {
            "success": False,
            "error": f"AppFlow.swift not found at {APPFLOW_PATH}",
        }

    contents = path.read_text(encoding="utf-8")

    match = _METHOD_RE.search(contents)
    if not match:
        return {
            "success": False,
            "error": "Could not locate setLaunchScreen method in AppFlow.swift",
        }

    # Build the new method body with all targets listed as comments
    # except the active one.
    active_line = _TARGETS[target]
    comment_lines = []
    for key, line in _TARGETS.items():
        if key == target:
            continue
        # Strip leading whitespace, add comment prefix, re-indent
        stripped = line.lstrip()
        comment_lines.append(f"//        {stripped}")

    body_parts = ["\n"]
    body_parts.append("//    Demo VC switcher — managed by devtools-mcp\n")
    for cl in comment_lines:
        body_parts.append(f"{cl}\n")
    body_parts.append(f"\n{active_line}\n")

    new_body = "".join(body_parts)
    replacement = f"{match.group(1)}{new_body}{match.group(3)}"
    new_contents = contents[: match.start()] + replacement + contents[match.end() :]

    path.write_text(new_contents, encoding="utf-8")

    return {
        "success": True,
        "target": target,
        "description": f"setLaunchScreen now launches: {target}",
        "file": str(path),
    }


def get_current_target() -> dict:
    """Read AppFlow.swift and detect which demo VC target is currently active.

    Returns:
        Dict with the current target name or 'unknown'.
    """
    path = Path(APPFLOW_PATH)
    if not path.exists():
        return {
            "success": False,
            "error": f"AppFlow.swift not found at {APPFLOW_PATH}",
        }

    contents = path.read_text(encoding="utf-8")
    match = _METHOD_RE.search(contents)
    if not match:
        return {"success": False, "error": "Could not locate setLaunchScreen method"}

    body = match.group(2)

    # Find the uncommented referenceController assignment
    for key, line in _TARGETS.items():
        # Check if this line appears uncommented in the body
        stripped = line.strip()
        for body_line in body.split("\n"):
            clean = body_line.strip()
            # Skip commented lines
            if clean.startswith("//"):
                continue
            if stripped in clean:
                return {
                    "success": True,
                    "current_target": key,
                    "valid_targets": VALID_TARGETS,
                }

    return {
        "success": True,
        "current_target": "unknown",
        "valid_targets": VALID_TARGETS,
    }
