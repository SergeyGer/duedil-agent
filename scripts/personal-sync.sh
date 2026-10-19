#!/usr/bin/env bash
# Copy the files that git does NOT carry between the Linux server and a laptop.
#
#   ./scripts/personal-sync.sh pull            server -> this checkout  (.env, the guide)
#   ./scripts/personal-sync.sh push            this checkout -> server
#   ./scripts/personal-sync.sh status          what differs, without copying anything
#   ./scripts/personal-sync.sh pull --dry-run  show the plan, copy nothing
#
# These are the personal files: `.env` (API keys) and `Run_Stop_Project.docx` (the guide
# generated for you). Both are gitignored on purpose, so git pull/push will never move
# them — this script is the alternative.
#
# Target host and directory (override any of them):
#   DUEDIL_SERVER=188.245.2.148        # host or an ~/.ssh/config alias
#   DUEDIL_USER=root                   # ssh user
#   DUEDIL_REMOTE_DIR=/root/projects/duedil-agent/duedil-agent
#
# Plain `scp` is used on purpose: it ships with Linux, macOS and Windows 10+, so the same
# command works from PowerShell, Git Bash and WSL.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

SERVER="${DUEDIL_SERVER:-188.245.2.148}"
USER_NAME="${DUEDIL_USER:-root}"
REMOTE_DIR="${DUEDIL_REMOTE_DIR:-/root/projects/duedil-agent/duedil-agent}"
TARGET="${USER_NAME}@${SERVER}:${REMOTE_DIR}"

# The files that must never be committed, and therefore must be carried by hand.
FILES=(.env Run_Stop_Project.docx Run_Stop_Project_EN.docx)

if [ -t 1 ]; then
    BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'
    YELLOW=$'\033[33m'; BLUE=$'\033[34m'; RESET=$'\033[0m'
else
    BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; BLUE=""; RESET=""
fi

say()  { printf '%s\n' "${BLUE}==>${RESET} ${BOLD}$*${RESET}"; }
ok()   { printf '%s\n' "${GREEN}  ok${RESET} $*"; }
warn() { printf '%s\n' "${YELLOW}  !${RESET} $*"; }
die()  { printf '%s\n' "${RED}  error${RESET} $*" >&2; exit 1; }

require_ssh() {
    command -v ssh >/dev/null 2>&1 || die "ssh is not installed (Windows: enable the OpenSSH client feature)"
    command -v scp >/dev/null 2>&1 || die "scp is not installed (Windows: enable the OpenSSH client feature)"
    # A short timeout keeps a wrong host from hanging the terminal.
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$USER_NAME@$SERVER" true 2>/dev/null \
        || die "cannot reach ${USER_NAME}@${SERVER} with keys (see the SSH section of Run_Stop_Project.docx)"
}

describe() {
    # size and mtime of a local file, or "(missing)"
    local file="$1"
    if [ -f "$file" ]; then
        printf '%s (%s, %s)' "$file" "$(wc -c < "$file" | tr -d ' ')" "$(date -r "$file" '+%Y-%m-%d %H:%M')"
    else
        printf '%s (missing)' "$file"
    fi
}

cmd_list_files() {
    local available=()
    for file in "${FILES[@]}"; do
        [ -f "$file" ] && available+=("$file")
    done
    [ "${#available[@]}" -gt 0 ] || die "nothing to copy: none of ${FILES[*]} exists here"
    printf '%s\n' "${available[@]}"
}

cmd_status() {
    require_ssh
    say "Local checkout: $PROJECT_DIR"
    for file in "${FILES[@]}"; do
        local local_state remote_state
        local_state="$(describe "$file")"
        remote_state="$(ssh -o BatchMode=yes "$USER_NAME@$SERVER" \
            "if [ -f ${REMOTE_DIR}/${file} ]; then echo \"\$(wc -c < ${REMOTE_DIR}/${file}) bytes, \$(date -r ${REMOTE_DIR}/${file} '+%%Y-%%m-%%d %%H:%%M')\"; else echo missing; fi" 2>/dev/null || echo "unreachable")"
        printf '  %-26s local: %s\n' "$file" "$local_state"
        printf '  %-26s remote: %s\n' "" "$remote_state"
    done
    printf '  %s.gitignore keeps these out of git on purpose — see the guide.%s\n' "$DIM" "$RESET"
}

cmd_push() {
    local dry="${1:-}"
    require_ssh
    local files=()
    while IFS= read -r line; do files+=("$line"); done < <(cmd_list_files)
    say "Uploading to ${TARGET}"
    for file in "${files[@]}"; do
        printf '  %s -> %s\n' "$(describe "$file")" "$file"
    done
    if [ "$dry" = "--dry-run" ]; then
        warn "dry run: nothing was copied"
        return 0
    fi
    scp -q "${files[@]}" "$TARGET/"
    ssh -o BatchMode=yes "$USER_NAME@$SERVER" "chmod 600 ${REMOTE_DIR}/.env 2>/dev/null || true"
    ok "uploaded ${#files[@]} file(s); .env is readable by its owner only"
}

cmd_pull() {
    local dry="${1:-}"
    require_ssh
    say "Downloading from ${TARGET}"
    local present=()
    for file in "${FILES[@]}"; do
        if ssh -o BatchMode=yes "$USER_NAME@$SERVER" "test -f ${REMOTE_DIR}/${file}" 2>/dev/null; then
            present+=("$file")
            printf '  %s/%s -> %s\n' "$REMOTE_DIR" "$file" "$(describe "$file")"
        fi
    done
    [ "${#present[@]}" -gt 0 ] || die "the server has none of ${FILES[*]}"
    if [ "$dry" = "--dry-run" ]; then
        warn "dry run: nothing was copied"
        return 0
    fi
    for file in "${present[@]}"; do
        if [ -f "$file" ] && [ "$file" = ".env" ]; then
            # Keep the previous secrets instead of silently overwriting them.
            cp "$file" "$file.bak.$(date '+%Y%m%d-%H%M%S')"
            warn "local .env backed up before the download"
        fi
        scp -q "${TARGET}/${file}" "./${file}"
    done
    chmod 600 .env 2>/dev/null || true
    ok "downloaded ${#present[@]} file(s)"
    printf '  %sNever commit these: .gitignore already excludes them.%s\n' "$DIM" "$RESET"
}

usage() {
    cat <<EOF
${BOLD}Personal files between the server and this laptop${RESET}

  ${BOLD}./scripts/personal-sync.sh status${RESET}            compare the local and remote copies
  ${BOLD}./scripts/personal-sync.sh pull${RESET}              server -> here  (.env, the guide)
  ${BOLD}./scripts/personal-sync.sh push${RESET}              here -> server
  ${BOLD}./scripts/personal-sync.sh pull --dry-run${RESET}    show the plan, copy nothing

  Files: ${FILES[*]}
  Target: ${TARGET}

  These files are gitignored, so git pull/push never moves them.
  Override the target with DUEDIL_SERVER, DUEDIL_USER and DUEDIL_REMOTE_DIR.
EOF
}

case "${1:-}" in
    status) cmd_status ;;
    pull)   cmd_pull "${2:-}" ;;
    push)   cmd_push "${2:-}" ;;
    ""|-h|--help|help) usage ;;
    *) die "unknown command '$1' (try --help)" ;;
esac
