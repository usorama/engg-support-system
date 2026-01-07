#!/bin/bash
#
# Install Veracity Daemon as a launchd agent
#
# This script:
# 1. Installs the veracityd control script
# 2. Creates the launchd plist
# 3. Loads the daemon to start on login
#
# Usage:
#   ./scripts/install-daemon.sh         # Install
#   ./scripts/install-daemon.sh remove  # Uninstall
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERACITY_ROOT="$(dirname "$SCRIPT_DIR")"
PLIST_TEMPLATE="$VERACITY_ROOT/infra/com.veracity.daemon.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.veracity.daemon.plist"
VERACITYD_SCRIPT="$VERACITY_ROOT/scripts/veracityd"

# Detect Python 3.11
PYTHON_PATH=""
if command -v /opt/homebrew/bin/python3.11 &> /dev/null; then
    PYTHON_PATH="/opt/homebrew/bin/python3.11"
elif command -v python3.11 &> /dev/null; then
    PYTHON_PATH="$(which python3.11)"
elif command -v python3 &> /dev/null; then
    PYTHON_PATH="$(which python3)"
fi

if [ -z "$PYTHON_PATH" ]; then
    echo "ERROR: Python 3 not found"
    exit 1
fi

install_daemon() {
    echo "=== Veracity Daemon Installation ==="
    echo ""
    echo "Python: $PYTHON_PATH"
    echo "Veracity Root: $VERACITY_ROOT"
    echo ""

    # Check dependencies
    echo "Checking dependencies..."
    if ! "$PYTHON_PATH" -c "import watchdog" 2>/dev/null; then
        echo "Installing watchdog..."
        "$PYTHON_PATH" -m pip install watchdog
    fi

    # Make veracityd executable
    chmod +x "$VERACITYD_SCRIPT"

    # Create LaunchAgents directory if needed
    mkdir -p "$HOME/Library/LaunchAgents"

    # Stop existing daemon if running
    if launchctl list | grep -q "com.veracity.daemon"; then
        echo "Stopping existing daemon..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    # Generate plist with correct paths
    echo "Creating launchd configuration..."
    sed -e "s|VERACITY_ROOT_PLACEHOLDER|$VERACITY_ROOT|g" \
        -e "s|/opt/homebrew/bin/python3.11|$PYTHON_PATH|g" \
        "$PLIST_TEMPLATE" > "$PLIST_DEST"

    # Load the daemon
    echo "Loading daemon..."
    launchctl load "$PLIST_DEST"

    echo ""
    echo "=== Installation Complete ==="
    echo ""
    echo "The Veracity daemon is now installed and running."
    echo ""
    echo "Next steps:"
    echo "  1. Register projects to watch:"
    echo "     veracityd register pinglearn ~/Projects/pinglearn/pinglearn-app"
    echo ""
    echo "  2. Check status:"
    echo "     veracityd status"
    echo ""
    echo "  3. View logs:"
    echo "     veracityd logs"
    echo ""
    echo "Add veracityd to your PATH:"
    echo "  echo 'export PATH=\"$VERACITY_ROOT/scripts:\$PATH\"' >> ~/.zshrc"
}

remove_daemon() {
    echo "=== Veracity Daemon Removal ==="
    echo ""

    # Stop and unload
    if launchctl list | grep -q "com.veracity.daemon"; then
        echo "Stopping daemon..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    # Remove plist
    if [ -f "$PLIST_DEST" ]; then
        echo "Removing launchd configuration..."
        rm -f "$PLIST_DEST"
    fi

    echo ""
    echo "Daemon removed."
    echo "Note: ~/.veracity/projects.yaml preserved (contains project registry)"
}

case "${1:-install}" in
    install)
        install_daemon
        ;;
    remove|uninstall)
        remove_daemon
        ;;
    *)
        echo "Usage: $0 [install|remove]"
        exit 1
        ;;
esac
