#!/usr/bin/env bash
set -e
echo "Starting Agentic Software Factory installation..."
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "Error: Python 3 is required to scaffold the Agentic Software Factory."
    exit 1
fi

$PY_BIN -c "$(curl -fsSL https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main/install.py)"
