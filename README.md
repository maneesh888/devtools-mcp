# DevTools MCP Server

A comprehensive MCP (Model Context Protocol) server for full-stack development, providing build automation, testing, and workflow tools for AI agents across all platforms.

**Current Status:**
- ✅ **iOS**: Complete (build, run, audit, demo tools)
- 🚧 **Android**: Planned (gradle, emulator, APK management)
- 🚧 **Web**: Planned (Playwright/Cypress, build tools, deployment)
- 🚧 **Server**: Planned (API testing, Docker, deployment automation)

## Features

### Mobile (iOS ✅ | Android 🚧)

#### iOS Tools Available Now
- **Build & Run**: xcodebuild orchestration with structured error parsing
- **Xcode Automation**: AppleScript run/stop controls (Cmd+R, Cmd+.)
- **Simulator Management**: List and target iOS simulators
- **Code Quality**: Pre-commit audits (Swift hygiene, design system, file metadata)
- **Demo Tools**: Quick VC switching for testing

#### Android Tools (Planned)
- Gradle build orchestration
- Emulator/device management
- APK/AAB build and installation
- Kotlin/Java code quality checks

### Web (Planned)
- **Browser Automation**: Playwright/Cypress test execution
- **Build Tools**: Vite/Next.js/React build orchestration
- **Deployment**: Vercel/Netlify/custom deployment helpers
- **E2E Testing**: Cross-browser test execution and reporting

### Server (Planned)
- **API Testing**: REST/GraphQL endpoint testing
- **Container Tools**: Docker build/run/compose orchestration
- **Deployment**: SSH-based deployment automation
- **Monitoring**: Health check runners, log parsing

## Setup

### 1. Install
```bash
cd devtools-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

### 2. Configure MCP Client

Add to your MCP config (e.g., `~/.config/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "devtools": {
      "command": "/absolute/path/to/devtools-mcp/.venv/bin/devtools-mcp",
      "args": [],
      "env": {
        "DEVTOOLS_IOS_PROJECT": "/path/to/YourApp.xcodeproj",
        "DEVTOOLS_IOS_SCHEME": "YourScheme",
        "DEVTOOLS_IOS_CONFIGURATION": "Debug",
        "DEVTOOLS_IOS_SIMULATOR": "iPhone 17 Pro"
      }
    }
  }
}
```

### 3. Restart Your AI Client

Tools will populate based on available platforms.

## Current Tools (iOS)

- `ios_build` — Build for simulator with error parsing
- `ios_list_simulators` — List available simulators
- `xcode_run_app` — Send Cmd+R to Xcode
- `xcode_stop_app` — Send Cmd+. to Xcode
- `audit_changed_files` — Pre-commit code quality checks
- `demo_set_launch_vc` / `demo_get_launch_vc` — Testing helpers

## Project Structure

```
src/devtools_mcp/
├── server.py              # MCP tool registry
├── platforms/
│   ├── base.py            # Platform driver interface
│   ├── ios.py             # iOS/Xcode driver ✅
│   ├── android.py         # Android/Gradle driver (planned)
│   ├── web.py             # Web build/test driver (planned)
│   └── server.py          # Server/API testing driver (planned)
├── audit/                 # Code quality checks
├── xcode_control.py       # iOS-specific AppleScript automation
└── demo.py                # iOS-specific demo helpers
```

## Remote Access (HTTP Mode)

For **container-to-host** access (e.g., OpenClaw/Clawdbot running in Docker accessing host Xcode):

```bash
# On host (macOS)
./start-http-server.sh
```

Server runs on `http://0.0.0.0:8080`. Container accesses via `http://host.docker.internal:8080`.

See **[HTTP_SERVER.md](HTTP_SERVER.md)** for:
- OpenClaw/Clawdbot configuration
- Auto-start on boot (LaunchDaemon)
- Environment variables

## Documentation

- **[SETUP.md](SETUP.md)** — Detailed setup and environment variables
- **[ROADMAP.md](ROADMAP.md)** — Implementation status and future plans
- **[PLATFORMS.md](PLATFORMS.md)** — Platform-specific guides
- **[HTTP_SERVER.md](HTTP_SERVER.md)** — Remote access and HTTP mode

## Development

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

---

*One MCP server for your entire dev stack.*
