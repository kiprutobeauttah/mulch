#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
  .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python -m mulch.launcher