# Running devtools-mcp as HTTP Server

By default, devtools-mcp runs as a **stdio** MCP server (stdin/stdout communication). For **remote access** (e.g., from a Docker container to host machine), you can run it as an **HTTP/SSE server**.

## Quick Start (HTTP Mode)

### On Your Mac (Host)

```bash
cd ~/projects/devtools-mcp

# Configure environment
export DEVTOOLS_MCP_TRANSPORT=sse
export DEVTOOLS_MCP_PORT=8080
export DEVTOOLS_MCP_HOST=0.0.0.0

# iOS project settings
export DEVTOOLS_IOS_PROJECT="/path/to/YourApp.xcodeproj"
export DEVTOOLS_IOS_SCHEME="YourScheme"
export DEVTOOLS_IOS_CONFIGURATION="Debug"
export DEVTOOLS_IOS_SIMULATOR="iPhone 15 Pro"

# Start server
.venv/bin/devtools-mcp
```

Server will start on `http://0.0.0.0:8080`

### From Container (OpenClaw/Clawdbot)

Add to gateway config (`~/.config/openclaw/gateway.yml` or via `openclaw config`):

```yaml
mcp:
  servers:
    devtools:
      url: http://host.docker.internal:8080
      transport: sse
      headers:
        Authorization: "Bearer optional-token-if-you-add-auth"
```

Or using `openclaw mcp set`:

```bash
openclaw mcp set devtools '{"url":"http://host.docker.internal:8080","transport":"sse"}'
```

Then restart gateway:
```bash
openclaw gateway restart
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVTOOLS_MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `sse` |
| `DEVTOOLS_MCP_PORT` | `8080` | Port for HTTP server (sse mode only) |
| `DEVTOOLS_MCP_HOST` | `0.0.0.0` | Host to bind (sse mode only) |
| `DEVTOOLS_IOS_PROJECT` | - | Path to .xcodeproj file |
| `DEVTOOLS_IOS_SCHEME` | - | Xcode scheme name |
| `DEVTOOLS_IOS_CONFIGURATION` | `Debug` | Build configuration |
| `DEVTOOLS_IOS_SIMULATOR` | - | Target simulator name |

## Run as LaunchDaemon (Auto-Start on macOS)

Create `~/Library/LaunchAgents/ai.devtools.mcp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.devtools.mcp</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/devtools-mcp/.venv/bin/python</string>
        <string>-m</string>
        <string>devtools_mcp.server</string>
    </array>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>DEVTOOLS_MCP_TRANSPORT</key>
        <string>sse</string>
        <key>DEVTOOLS_MCP_PORT</key>
        <string>8080</string>
        <key>DEVTOOLS_MCP_HOST</key>
        <string>0.0.0.0</string>
        <key>DEVTOOLS_IOS_PROJECT</key>
        <string>/path/to/YourApp.xcodeproj</string>
        <key>DEVTOOLS_IOS_SCHEME</key>
        <string>YourScheme</string>
        <key>DEVTOOLS_IOS_CONFIGURATION</key>
        <string>Debug</string>
        <key>DEVTOOLS_IOS_SIMULATOR</key>
        <string>iPhone 15 Pro</string>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/tmp/devtools-mcp.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/devtools-mcp.error.log</string>
</dict>
</plist>
```

**Load and start:**
```bash
launchctl load ~/Library/LaunchAgents/ai.devtools.mcp.plist
launchctl start ai.devtools.mcp

# Check status
launchctl list | grep devtools

# View logs
tail -f /tmp/devtools-mcp.log
tail -f /tmp/devtools-mcp.error.log
```

**Stop and unload:**
```bash
launchctl stop ai.devtools.mcp
launchctl unload ~/Library/LaunchAgents/ai.devtools.mcp.plist
```

## Verify It's Working

### From Host
```bash
curl http://localhost:8080
# Should return MCP server info
```

### From Container
```bash
# Inside the container
curl http://host.docker.internal:8080
```

### Check Available Tools
After configuring in OpenClaw:
```bash
openclaw mcp show devtools
```

Then in your chat with Coder agent, ask:
> "What iOS development tools do you have?"

You should see: `ios_build`, `ios_list_simulators`, `xcode_run_app`, etc.

## Troubleshooting

**Container can't reach host:**
```bash
# From container, test connectivity
ping host.docker.internal
curl http://host.docker.internal:8080
```

**Port already in use:**
```bash
# Find what's using port 8080
lsof -i :8080

# Use a different port
export DEVTOOLS_MCP_PORT=8081
```

**Server not starting:**
```bash
# Check logs
tail -f /tmp/devtools-mcp.log
tail -f /tmp/devtools-mcp.error.log

# Test manually
cd ~/projects/hobby/devtools-mcp
DEVTOOLS_MCP_TRANSPORT=sse DEVTOOLS_MCP_PORT=8080 .venv/bin/devtools-mcp
```

---

**Two modes, same server:**
- **stdio**: For Claude Code on the same machine
- **HTTP/SSE**: For remote access from containers/other machines
