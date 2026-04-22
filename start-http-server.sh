#!/bin/bash
# Start devtools-mcp as HTTP server for container access

set -e

# Configuration
export DEVTOOLS_MCP_TRANSPORT=sse
export DEVTOOLS_MCP_PORT=${DEVTOOLS_MCP_PORT:-8888}
export DEVTOOLS_MCP_HOST=${DEVTOOLS_MCP_HOST:-0.0.0.0}

# iOS project settings (customize these or set via environment variables)
export DEVTOOLS_IOS_PROJECT="${DEVTOOLS_IOS_PROJECT:-/path/to/YourApp.xcodeproj}"
export DEVTOOLS_IOS_SCHEME="${DEVTOOLS_IOS_SCHEME:-YourScheme}"
export DEVTOOLS_IOS_CONFIGURATION="${DEVTOOLS_IOS_CONFIGURATION:-Debug}"
export DEVTOOLS_IOS_SIMULATOR="${DEVTOOLS_IOS_SIMULATOR:-iPhone 15 Pro}"

echo "======================================"
echo "  DevTools MCP HTTP Server"
echo "======================================"
echo ""
echo "Transport:     sse (HTTP)"
echo "Bind:          ${DEVTOOLS_MCP_HOST}:${DEVTOOLS_MCP_PORT}"
echo "Project:       ${DEVTOOLS_IOS_PROJECT}"
echo "Scheme:        ${DEVTOOLS_IOS_SCHEME}"
echo "Configuration: ${DEVTOOLS_IOS_CONFIGURATION}"
echo "Simulator:     ${DEVTOOLS_IOS_SIMULATOR}"
echo ""
echo "Access from container:"
echo "  http://host.docker.internal:${DEVTOOLS_MCP_PORT}"
echo ""
echo "Press Ctrl+C to stop"
echo "======================================"
echo ""

# Find script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start server
exec "${SCRIPT_DIR}/.venv/bin/devtools-mcp"
