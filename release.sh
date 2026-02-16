#!/bin/bash
# Helper script to publish Astra Engine to PyPI

# Ensure we are in the right directory
cd "$(dirname "$0")"

# Create/Activate virtual environment for build tools
if [ ! -d ".build_venv" ]; then
    echo "Creating build environment..."
    python3 -m venv .build_venv
    source .build_venv/bin/activate
    pip install build twine
else
    source .build_venv/bin/activate
fi

# Upload to PyPI
echo "🚀 Uploading to PyPI..."
echo "Username: __token__"
echo "Password: <your_pypi_api_token>"
twine upload dist/*
