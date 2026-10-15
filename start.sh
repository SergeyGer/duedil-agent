#!/usr/bin/env bash
# Convenience wrapper so the commands are short from the repository root:
#
#   ./start.sh          same as ./scripts/project.sh start
#   ./stop.sh           same as ./scripts/project.sh stop
#
# On Windows use start.cmd / stop.cmd (or .\scripts\project.ps1 directly).

set -euo pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$BASE/scripts/project.sh" start "$@"
