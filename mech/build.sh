#!/bin/sh
set -eu
cd "$(dirname "$0")"
# Python：优先用环境变量 FL_PYTHON（需装 build123d、trimesh、ezdxf、matplotlib），否则用默认虚拟环境，再不行用 python3
py="${FL_PYTHON:-$HOME/.local/share/filllight/venv/bin/python}"
[ -x "$py" ] || py=python3
exec "$py" -B -u export.py
