#!/bin/bash
set -e

cd "$(dirname "$0")/scripts"

# Install dependencies if needed
if ! python3 -c "import pandas, plotly, openpyxl" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -q -r requirements.txt
fi

python3 main.py
