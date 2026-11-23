#!/bin/sh
set -eu
cd "$(dirname "$0")"
py="$HOME/.local/share/filllight/venv/bin/python"
case "${1:-all}" in
 C|c) exec "$py" -B frozen08.py --deep ;;
 A2|a2) exec "$py" -B -u a2_build.py ;;
 all) "$py" -B -u a2_build.py; exec "$py" -B frozen08.py --deep ;;
 *) echo '用法：mech/build.sh [C|A2|all]' >&2; exit 2 ;;
esac
