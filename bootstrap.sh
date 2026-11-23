#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "===================================================================="
echo "        XENONITE 4-LAYER STACK - 1-CLICK BOOTSTRAP (UNIX)"
echo "===================================================================="

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python 3.10+ not found. Please install Python 3.10 or newer."
    exit 1
fi

python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" || {
    echo "[ERROR] Python >= 3.10 is required."
    exit 1
}

if [ ! -d ".venv" ]; then
    echo "[*] Creating isolated virtual environment (.venv)..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! python3 -c "import xenonite_stack, mcp" >/dev/null 2>&1; then
    echo "[*] Installing xenonite-stack and MCP SDK..."
    pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
    pip install -e .
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "[*] Created default .env from .env.example"
fi

echo ""
xenonite check

echo ""
echo "===================================================================="
echo "Bootstrap complete! Next steps:"
echo "  1. Install globally into Antigravity : xenonite install"
echo "  2. Or print MCP JSON for Cursor/IDE  : xenonite print-mcp"
echo "  3. Optional full Docker L1+L2 stack  : xenonite docker up full"
echo "  4. Verify everything                 : xenonite verify"
echo "===================================================================="
