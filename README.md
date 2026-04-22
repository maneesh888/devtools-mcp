# DevTools MCP Server

An MCP (Model Context Protocol) server that gives AI agents real development tools: build automation, simulator/emulator management, code quality audits, and Xcode control. One server, multiple platforms.

## Current Status

- **iOS**: Build, run, audit, Xcode automation
- **Android**: In progress (Gradle, emulator, APK, Kotlin lint)
- **Web**: Planned (Vite/Next.js builds, testing, deploy)
- **Server/Backend**: Planned (Docker, API testing, migrations)

## What It Does

AI agents (Claude Code, OpenClaw, etc.) can't run xcodebuild, manage simulators, or trigger Xcode. This MCP server bridges that gap.

**iOS tools available now:**

- `ios_build` - Build for simulator with structured error parsing (file, line, column, message). Auto-runs in Xcode on success.
- `ios_list_simulators` - List available simulators with UDID, state, OS version.
- `xcode_run_app` / `xcode_stop_app` - Send Cmd+R / Cmd+. to Xcode via AppleScript.
- `audit_changed_files` - Pre-commit audits: design system compliance, Swift hygiene (print/try!/fatalError/TODO), file metadata checks. Designed to run in parallel with builds.

## Setup

```bash
cd devtools-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Configure Your MCP Client

Add to your MCP config:

```json
{
  "mcpServers": {
    "devtools": {
      "command": "/path/to/devtools-mcp/.venv/bin/devtools-mcp",
      "env": {
        "DEVTOOLS_IOS_PROJECT": "/path/to/YourApp.xcodeproj",
        "DEVTOOLS_IOS_SCHEME": "YourScheme",
        "DEVTOOLS_IOS_SIMULATOR": "iPhone 16 Pro"
      }
    }
  }
}
```

Or pass `project_path` and `scheme` directly when calling tools.

### Multi-Project Support

Create a `mcp_helper.json` in the repo root to map container paths to host paths:

```json
{
  "host_workspace": "/Users/you/Projects"
}
```

Useful when the MCP server runs on a host Mac but agents run in Docker. The agent reads this file to translate its local paths to host-side paths for MCP calls.

## Remote Access (SSE Mode)

For container-to-host setups (e.g., AI agents in Docker calling Xcode on the host Mac):

```bash
.venv/bin/devtools-mcp --transport sse --port 7888
```

Agents connect via `http://host.docker.internal:7888/sse`. See [HTTP_SERVER.md](HTTP_SERVER.md) for details.

## Project Structure

```
src/devtools_mcp/
  server.py              # MCP tool registry and entry point
  platforms/
    base.py              # Shared BuildResult/BuildError types
    ios.py               # iOS/Xcode driver
    android.py           # Android/Gradle driver (in progress)
    web.py               # Web driver (planned)
  audit/                 # Code quality checks
  xcode_control.py       # AppleScript automation for Xcode
```

## Development

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## License

MIT
