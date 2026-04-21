"""Xcode accessibility-based control via AppleScript and System Events.

Sends keyboard shortcuts and reads UI state from a running Xcode instance.
Requires macOS Accessibility permissions for the calling process.
"""

from __future__ import annotations

import subprocess

_TIMEOUT = 10


def _run_applescript(script: str, timeout: int = _TIMEOUT) -> dict:
    """Execute an AppleScript snippet and return the result."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip()
            if "not running" in err.lower() or "Can't get application" in err:
                return {"success": False, "error": "Xcode is not running."}
            return {"success": False, "error": err}
        return {"success": True, "output": proc.stdout.strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"AppleScript timed out after {timeout}s."}
    except FileNotFoundError:
        return {"success": False, "error": "osascript not found — this tool requires macOS."}


def _send_keystroke(key: str, modifiers: str = "command down") -> dict:
    """Send a keystroke to Xcode via System Events."""
    script = f'''
        tell application "System Events"
            if not (exists process "Xcode") then
                error "Xcode is not running."
            end if
            tell process "Xcode"
                set frontmost to true
                keystroke "{key}" using {{{modifiers}}}
            end tell
        end tell
        return "ok"
    '''
    return _run_applescript(script)


def _stop_and_dismiss() -> None:
    """Stop any running session in Xcode and dismiss the confirmation dialog.

    Sends Cmd+. to stop, waits briefly, then clicks the 'Stop' button
    on the confirmation sheet if it appears. Safe to call when nothing
    is running — the keystroke and button click are silently ignored.
    """
    script = '''
        tell application "System Events"
            if not (exists process "Xcode") then return "no_xcode"
            tell process "Xcode"
                set frontmost to true
                -- Send Cmd+. to request stop
                keystroke "." using {command down}
                delay 0.5
                -- Dismiss the "Stop" confirmation sheet if it appeared
                try
                    set w to front window
                    repeat with s in (every sheet of w)
                        try
                            click button "Stop" of s
                        end try
                    end repeat
                end try
            end tell
        end tell
        return "ok"
    '''
    _run_applescript(script)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def xcode_run() -> dict:
    """Send Cmd+R to Xcode (Build & Run).

    Automatically stops any running session first and dismisses
    the 'Stop' confirmation dialog if it appears.
    """
    _stop_and_dismiss()
    result = _send_keystroke("r")
    if result["success"]:
        return {"success": True, "action": "Stopped previous run (if any), then sent Cmd+R (Run) to Xcode."}
    return result


def xcode_stop() -> dict:
    """Send Cmd+. to Xcode (Stop)."""
    script = '''
        tell application "System Events"
            if not (exists process "Xcode") then
                error "Xcode is not running."
            end if
            tell process "Xcode"
                set frontmost to true
                keystroke "." using {command down}
            end tell
        end tell
        return "ok"
    '''
    result = _run_applescript(script)
    if result["success"]:
        return {"success": True, "action": "Sent Cmd+. (Stop) to Xcode."}
    return result


def xcode_build() -> dict:
    """Send Cmd+B to Xcode (Build).

    Automatically stops any running session first.
    """
    _stop_and_dismiss()
    result = _send_keystroke("b")
    if result["success"]:
        return {"success": True, "action": "Stopped previous run (if any), then sent Cmd+B (Build) to Xcode."}
    return result


def xcode_clean_build() -> dict:
    """Send Cmd+Shift+K (Clean) then Cmd+B (Build) to Xcode.

    Automatically stops any running session first.
    """
    _stop_and_dismiss()
    script = '''
        tell application "System Events"
            if not (exists process "Xcode") then
                error "Xcode is not running."
            end if
            tell process "Xcode"
                set frontmost to true
                keystroke "k" using {command down, shift down}
                delay 1
                keystroke "b" using {command down}
            end tell
        end tell
        return "ok"
    '''
    result = _run_applescript(script)
    if result["success"]:
        return {"success": True, "action": "Stopped previous run (if any), then sent Cmd+Shift+K (Clean) + Cmd+B (Build) to Xcode."}
    return result


def xcode_get_build_status() -> dict:
    """Read Xcode's activity status text from the toolbar.

    This reads AXStaticText elements from Xcode's toolbar area to find
    the build/run status (e.g. 'Build Succeeded', 'Running YourApp on iPhone 17 Pro').
    """
    script = '''
        tell application "System Events"
            if not (exists process "Xcode") then
                error "Xcode is not running."
            end if
            tell process "Xcode"
                try
                    -- The activity text lives in the toolbar area
                    set statusTexts to {}
                    set allWindows to every window
                    repeat with w in allWindows
                        try
                            set toolbarGroups to every group of w
                            repeat with g in toolbarGroups
                                try
                                    set staticTexts to every static text of g
                                    repeat with t in staticTexts
                                        set txt to value of t
                                        if txt is not "" and txt is not missing value then
                                            set end of statusTexts to txt
                                        end if
                                    end repeat
                                end try
                                -- Also check nested groups (toolbar often has sub-groups)
                                try
                                    set subGroups to every group of g
                                    repeat with sg in subGroups
                                        try
                                            set subTexts to every static text of sg
                                            repeat with st in subTexts
                                                set stxt to value of st
                                                if stxt is not "" and stxt is not missing value then
                                                    set end of statusTexts to stxt
                                                end if
                                            end repeat
                                        end try
                                    end repeat
                                end try
                            end repeat
                        end try
                    end repeat
                    if (count of statusTexts) = 0 then
                        return "NO_STATUS_FOUND"
                    end if
                    set AppleScript's text item delimiters to "|||"
                    return statusTexts as text
                on error errMsg
                    error errMsg
                end try
            end tell
        end tell
    '''
    result = _run_applescript(script, timeout=15)
    if not result["success"]:
        return result

    raw = result["output"]
    if raw == "NO_STATUS_FOUND":
        return {"success": True, "status_texts": [], "message": "No status text found in Xcode toolbar."}

    texts = [t.strip() for t in raw.split("|||") if t.strip()]
    return {"success": True, "status_texts": texts}


def xcode_get_errors() -> dict:
    """Read build errors/warnings from Xcode's Issue Navigator.

    Opens the Issue Navigator (Cmd+5) and reads the accessible text elements.
    """
    script = '''
        tell application "System Events"
            if not (exists process "Xcode") then
                error "Xcode is not running."
            end if
            tell process "Xcode"
                set frontmost to true
                -- Open Issue Navigator (Cmd+5)
                keystroke "5" using {command down}
                delay 0.5

                set issueTexts to {}
                set allWindows to every window
                repeat with w in allWindows
                    try
                        -- The navigator is typically in a split group / scroll area
                        set outlines to every outline of every scroll area of every splitter group of w
                        repeat with ol in outlines
                            try
                                set rows to every row of ol
                                repeat with r in rows
                                    try
                                        set cells to every UI element of r
                                        repeat with c in cells
                                            try
                                                set cellTexts to every static text of c
                                                repeat with ct in cellTexts
                                                    set ctVal to value of ct
                                                    if ctVal is not "" and ctVal is not missing value then
                                                        set end of issueTexts to ctVal
                                                    end if
                                                end repeat
                                            end try
                                        end repeat
                                    end try
                                end repeat
                            end try
                        end repeat
                    end try
                end repeat

                if (count of issueTexts) = 0 then
                    return "NO_ISSUES_FOUND"
                end if
                set AppleScript's text item delimiters to "|||"
                return issueTexts as text
            end tell
        end tell
    '''
    result = _run_applescript(script, timeout=15)
    if not result["success"]:
        return result

    raw = result["output"]
    if raw == "NO_ISSUES_FOUND":
        return {"success": True, "issues": [], "message": "No issues found in Xcode Issue Navigator."}

    issues = [t.strip() for t in raw.split("|||") if t.strip()]
    return {"success": True, "issues": issues, "issue_count": len(issues)}
