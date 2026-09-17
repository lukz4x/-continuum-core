#!/bin/sh
set -eu

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from python.org, then run this script again."
  exit 1
fi

python_version="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "Python 3.10 or newer is required. Found Python $python_version."
  exit 1
}

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

echo "Setup complete with Python $python_version."
echo "Next: source .venv/bin/activate && continuum init"

