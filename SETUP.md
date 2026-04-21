# Setup Guide

## Quick Start

```bash
cd devtools-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Environment Variables

All platform-specific configuration is done via environment variables with a consistent naming scheme:

```
DEVTOOLS_<PLATFORM>_<SETTING>
```

### iOS Configuration

```bash
export DEVTOOLS_IOS_PROJECT="/path/to/YourApp.xcodeproj"
export DEVTOOLS_IOS_SCHEME="YourScheme"
export DEVTOOLS_IOS_CONFIGURATION="Debug"  # or "Release"
export DEVTOOLS_IOS_SIMULATOR="iPhone 17 Pro"
export DEVTOOLS_IOS_DERIVED_DATA="$HOME/Library/Developer/Xcode/DerivedData-MCP"

# Optional: For demo VC switcher
export DEVTOOLS_IOS_APPFLOW_PATH="/path/to/AppFlow.swift"

# Optional: For localization tools (if enabled)
export DEVTOOLS_IOS_XCSTRINGS="/path/to/Localizable.xcstrings"
```

### Android Configuration (Planned)

```bash
export DEVTOOLS_ANDROID_PROJECT="/path/to/android-project"
export DEVTOOLS_ANDROID_MODULE="app"
export DEVTOOLS_ANDROID_BUILD_VARIANT="debug"
export DEVTOOLS_ANDROID_EMULATOR="Pixel_7_API_34"
export DEVTOOLS_ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
```

### Web Configuration (Planned)

```bash
export DEVTOOLS_WEB_PROJECT="/path/to/web-project"
export DEVTOOLS_WEB_BUILD_CMD="npm run build"
export DEVTOOLS_WEB_TEST_CMD="npm run test"
export DEVTOOLS_WEB_PREVIEW_PORT="3000"
export DEVTOOLS_WEB_BROWSER="chromium"  # for Playwright
```

### Server Configuration (Planned)

```bash
export DEVTOOLS_SERVER_PROJECT="/path/to/server-project"
export DEVTOOLS_SERVER_TEST_CMD="npm test"
export DEVTOOLS_SERVER_DOCKER_COMPOSE="/path/to/docker-compose.yml"
export DEVTOOLS_SERVER_API_BASE_URL="http://localhost:8000"
```

## MCP Client Configuration

### Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "devtools": {
      "command": "/absolute/path/to/devtools-mcp/.venv/bin/devtools-mcp",
      "args": [],
      "env": {
        "DEVTOOLS_IOS_PROJECT": "/Users/you/projects/YourApp.xcodeproj",
        "DEVTOOLS_IOS_SCHEME": "YourScheme",
        "DEVTOOLS_IOS_CONFIGURATION": "Debug",
        "DEVTOOLS_IOS_SIMULATOR": "iPhone 17 Pro",
        
        "DEVTOOLS_ANDROID_PROJECT": "/Users/you/projects/android-app",
        "DEVTOOLS_ANDROID_MODULE": "app",
        
        "DEVTOOLS_WEB_PROJECT": "/Users/you/projects/web-app",
        "DEVTOOLS_WEB_BUILD_CMD": "npm run build"
      }
    }
  }
}
```

### Cline / Other Clients

Adjust the config format according to your client's MCP server requirements.

## Verify Installation

```bash
# Check the binary exists
ls -la .venv/bin/devtools-mcp

# Test with a simple invocation (requires valid env vars for active platforms)
.venv/bin/devtools-mcp
```

## Platform-Specific Setup

### iOS
1. Xcode must be installed and command-line tools configured
2. Project must be buildable from command line (`xcodebuild`)
3. Simulator must exist (check with `xcrun simctl list`)

### Android (When Implemented)
1. Android SDK installed
2. `ANDROID_HOME` or `ANDROID_SDK_ROOT` set
3. Gradle wrapper in project root
4. AVD created (check with `avdmanager list avd`)

### Web (When Implemented)
1. Node.js installed (or appropriate runtime)
2. Dependencies installed (`npm install`, `yarn`, etc.)
3. Build/test scripts defined in `package.json`

### Server (When Implemented)
1. Runtime environment configured (Node/Python/Go/etc.)
2. Docker installed (if using container tools)
3. Test framework configured

## Git Setup (Optional)

```bash
cd devtools-mcp
git init
git add .
git commit -m "Initial: DevTools MCP server"
```

## Pre-Commit Hook (iOS)

```bash
# From your iOS project root
ln -sf /path/to/devtools-mcp/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### iOS Build Fails
- Verify Xcode command-line tools: `xcode-select -p`
- Check simulator exists: `xcrun simctl list devices`
- Try building manually: `xcodebuild -project <path> -scheme <scheme> -destination 'platform=iOS Simulator,name=<simulator>'`

### MCP Server Not Showing Tools
- Check client logs for connection errors
- Verify virtual environment is activated
- Ensure env vars are set correctly in MCP config
- Restart the MCP client after config changes

---

*For platform-specific guides, see [PLATFORMS.md](PLATFORMS.md)*
