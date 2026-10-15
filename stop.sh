#!/usr/bin/env bash
# Convenience wrapper so the commands are short from the repository root:
#
#   ./stop.sh           same as ./scripts/project.sh stop
#
# On Windows use stop.cmd (or .\scripts\project.ps1 stop directly).

set -euo pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$BASE/scripts/project.sh" stop "$@"
