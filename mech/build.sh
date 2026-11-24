#!/bin/sh
set -eu
cd "$(dirname "$0")"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export MPLCONFIGDIR="$PWD/out/.cache/mpl" XDG_CACHE_HOME="$PWD/out/.cache"
mkdir -p "$MPLCONFIGDIR" out/round11
exec "$HOME/.local/share/filllight/venv/bin/python" -B -u v05_build.py "${1:-all}"
