#!/bin/bash
set -e

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Check uv ---
if ! command -v uv &>/dev/null; then
    error "uv is not installed."
    echo ""
    echo "Install with one of:"
    echo "  macOS/Homebrew:  brew install uv"
    echo "  Linux/macOS:     curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  Windows:         powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\""
    echo ""
    echo "See: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# --- Init if needed ---
if [ ! -f "pyproject.toml" ]; then
    warn "pyproject.toml not found. Initializing project..."
    uv init --no-readme
    uv add pandas plotly openpyxl
fi

# --- Sync dependencies ---
if [ ! -d ".venv" ]; then
    info "Creating virtual environment and installing dependencies..."
else
    info "Syncing dependencies..."
fi
uv sync --quiet

# --- Check data files ---
missing=0
for f in "注册漏斗-国家渠道-全部-1年.csv" "注册漏斗-国家渠道-去羊毛-1年.csv"; do
    if [ ! -f "$f" ]; then
        error "Missing data file: $f"
        missing=1
    fi
done
if [ "$missing" -eq 1 ]; then
    echo ""
    echo "Please export the two CSV files from the admin panel and place them in:"
    echo "  $(pwd)/"
    exit 1
fi

# --- Run ---
info "Generating report..."
uv run python scripts/main.py
