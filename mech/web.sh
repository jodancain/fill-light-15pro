#!/bin/sh
set -eu
cd "$(dirname "$0")"
py="$HOME/.local/share/filllight/venv/bin/python"
case "${1:-check}" in
 check) if [ "$#" -gt 0 ]; then shift; fi; exec "$py" -B verify_web.py "$@" ;;
 serve) exec "$py" -B -m http.server "${2:-8000}" --bind 127.0.0.1 --directory ../web ;;
 *) echo '用法：mech/web.sh check [--require-tcp] | serve [端口]' >&2; exit 2 ;;
esac
