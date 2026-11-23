#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec "$HOME/.local/share/filllight/venv/bin/python" -B -u export.py
