#!/bin/bash
#
# Setup ESS HTTP server to auto-start on macOS
#
# This installs a launchd service that starts the ESS HTTP server
# automatically when you log in. Required for hooks to work without Docker.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_SRC="${SCRIPT_DIR}/com.ess.http-server.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.ess.http-server.plist"

echo "ESS HTTP Server Auto-Start Setup"
echo "================================="
echo ""

# Check if already installed
if [[ -f "$PLIST_DST" ]]; then
    echo "Service already installed. Unloading old version..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# Copy plist
echo "Installing launchd service..."
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

# Update paths in plist to use current user's paths
sed -i '' "s|/Users/umasankr|$HOME|g" "$PLIST_DST"

# Load service
echo "Starting service..."
launchctl load "$PLIST_DST"

# Verify
sleep 2
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo ""
    echo "SUCCESS: ESS HTTP server is running!"
    echo ""
    echo "Service status:"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo ""
    echo "WARNING: Server may still be starting..."
    echo "Check logs: tail -f /tmp/ess-http-server.log"
fi

echo ""
echo "Management commands:"
echo "  Stop:    launchctl unload ~/Library/LaunchAgents/com.ess.http-server.plist"
echo "  Start:   launchctl load ~/Library/LaunchAgents/com.ess.http-server.plist"
echo "  Logs:    tail -f /tmp/ess-http-server.log"
echo "  Errors:  tail -f /tmp/ess-http-server.error.log"
