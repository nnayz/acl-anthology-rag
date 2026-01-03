#!/bin/bash
# Wrapper script for setup-env.py
# Usage: ./scripts/env-gen.sh [--non-interactive] [--skip-api] [--skip-client]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    exit 1
fi

# Run the Python script
exec python3 "$SCRIPT_DIR/env-gen.py" "$@"