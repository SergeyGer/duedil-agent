#!/usr/bin/env bash
# DueDil.Agent — start/stop helper for Linux, macOS and WSL.
#
# Nothing in this project runs by itself: the compose services use `restart: "no"`, so
# they never come back after a server reboot or a Docker daemon restart. This script is
# the normal way to bring them up and take them down again.
#
#   ./scripts/project.sh start        # build if needed, start, wait until healthy
#   ./scripts/project.sh stop         # stop and remove the containers (data is kept)
#   ./scripts/project.sh status       # what is running right now
#   ./scripts/project.sh logs         # follow the app log
#   ./scripts/project.sh --help       # everything else
#
# Windows PowerShell users have the same commands in scripts/project.ps1.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
IMAGE="duedil-agent:latest"

# Colours only when attached to a terminal, so piping to a file stays readable.
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

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

require_docker() {
    command -v docker >/dev/null 2>&1 || die "docker is not installed or not on PATH"
    docker compose version >/dev/null 2>&1 || die "the docker compose plugin is missing (need Compose v2)"
    docker info >/dev/null 2>&1 || die "the Docker daemon is not running. Start it (Linux: sudo systemctl start docker, Docker Desktop: launch the app) and try again."
}

port_of() {
    # The published port may differ if the compose file was edited or DUEDIL_PORT is set.
    compose port ui 8501 2>/dev/null | awk -F: 'NF>1 {print $NF}' | head -1
}

ui_id() {
    # No fixed container name: compose names it after the (per-developer) project, so the
    # id is looked up instead of assumed.
    compose ps -q ui 2>/dev/null | head -1
}

project_name() {
    compose config 2>/dev/null | sed -n 's/^name: //p' | head -1
}

wait_for_health() {
    local port="${1:-8501}" deadline=$((SECONDS + 180))
    printf '  waiting for the app to become healthy'
    while [ "$SECONDS" -lt "$deadline" ]; do
        local state id
        id="$(ui_id)"
        state="$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null || echo missing)"
        case "$state" in
            healthy) printf '\n'; ok "app is up: ${BOLD}http://localhost:${port}${RESET}"; return 0 ;;
            unhealthy) printf '\n'; die "the container reports unhealthy. Run: ./scripts/project.sh logs" ;;
        esac
        printf '.'
        sleep 3
    done
    printf '\n'
    warn "still not healthy after 3 minutes — showing the last log lines"
    compose logs --tail 20 ui || true
    return 1
}

cmd_start() {
    require_docker
    say "Starting DueDil.Agent"
    compose up -d --build
    wait_for_health "$(port_of || echo 8501)"
    printf '  %sStop it later with: ./scripts/project.sh stop%s\n' "$DIM" "$RESET"
}

cmd_stop() {
    require_docker
    say "Stopping DueDil.Agent"
    compose down --remove-orphans
    ok "containers removed; generated memos stay in the '$(project_name)_duedil-data' volume"
    printf '  %sThe port is free again — other projects on this machine are unaffected.%s\n' "$DIM" "$RESET"
}

cmd_restart() { cmd_stop; cmd_start; }

free_port() {
    local port="${1:-8501}"
    while [ "$port" -lt 8600 ]; do
        if ! (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -qE "[:.]${port}\b"; then
            printf '%s' "$port"
            return 0
        fi
        port=$((port + 1))
    done
    printf '%s' "$1"
}

cmd_instance() {
    local name="${1:-}" port="${2:-}" env_file="$PROJECT_DIR/.env"
    if [ -z "$name" ]; then
        say "This checkout's instance"
        printf '  compose project : %s\n' "$(project_name)"
        printf '  host port       : %s\n' "$(port_of || printf '%s' "${DUEDIL_PORT:-8501}")"
        printf '  url when running: http://localhost:%s\n' "$(port_of || printf '%s' "${DUEDIL_PORT:-8501}")"
        printf '  %sEvery developer on a shared server needs their own name and port:%s\n' "$DIM" "$RESET"
        printf '  %s./scripts/project.sh instance auto   # derive both from your username%s\n' "$DIM" "$RESET"
        return 0
    fi

    if [ "$name" = "auto" ]; then
        name="duedil-agent-$(whoami | tr 'A-Z' 'a-z' | tr -cd 'a-z0-9-')"
        port="$(free_port "${DUEDIL_PORT:-8501}")"
    else
        name="$(printf '%s' "$name" | tr 'A-Z' 'a-z' | tr -cd 'a-z0-9-')"
        port="${port:-$(free_port "${DUEDIL_PORT:-8501}")}"
    fi

    # Namespace the name: "alice" alone could collide with an unrelated compose project
    # on the same Docker host.
    case "$name" in
        duedil-agent*) : ;;
        *) name="duedil-agent-${name}" ;;
    esac

    case "$name" in
        ""|-*) die "the instance name must contain letters or digits" ;;
    esac
    case "$port" in
        ""|*[!0-9]*) die "the port must be a number, got '$port'" ;;
    esac

    say "Configuring this checkout as ${BOLD}${name}${RESET} on port ${BOLD}${port}${RESET}"
    if [ ! -f "$env_file" ]; then
        warn "no .env yet — copy it first: cp env.example .env (it also holds the API keys)"
        printf '# Created by ./scripts/project.sh instance\n' > "$env_file"
    fi
    # Drop the previous values, then append the current ones: compose reads .env itself.
    grep -vE '^(COMPOSE_PROJECT_NAME|DUEDIL_PORT)=' "$env_file" > "$env_file.tmp" || true
    mv "$env_file.tmp" "$env_file"
    printf '\n# --- dev instance: written by ./scripts/project.sh instance ---\n' >> "$env_file"
    printf 'COMPOSE_PROJECT_NAME=%s\nDUEDIL_PORT=%s\n' "$name" "$port" >> "$env_file"
    chmod 600 "$env_file"
    ok "written to .env (kept out of git by .gitignore)"
    printf '  %sNext: ./scripts/project.sh start -> http://localhost:%s%s\n' "$DIM" "$port" "$RESET"
}

cmd_status() {
    require_docker
    local name id
    name="$(project_name)"
    say "Instance ${BOLD}${name}${RESET}"
    docker ps -a --filter "label=com.docker.compose.project=${name}" \
        --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | sed 's/^/  /'
    id="$(ui_id)"
    if [ -n "$id" ] && docker inspect "$id" >/dev/null 2>&1; then
        say "Health"
        docker inspect -f '  state={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}} restart-policy={{.HostConfig.RestartPolicy.Name}}' "$id"
        local port; port="$(port_of || true)"
        [ -n "${port:-}" ] && printf '  url=http://localhost:%s\n' "$port"
    else
        warn "the UI container does not exist: the project is stopped"
    fi
    say "Auto-start settings on this machine"
    if command -v systemctl >/dev/null 2>&1; then
        printf '  docker daemon enabled at boot: %s\n' "$(systemctl is-enabled docker 2>/dev/null || echo unknown)"
    fi
    printf '  project containers restart policy: no (nothing here starts by itself)\n'
}

cmd_logs() {
    require_docker
    compose logs -f --tail 80 ui
}

cmd_build() {
    require_docker
    say "Building $IMAGE"
    compose build --pull ui
    ok "image built"
}

cmd_rebuild() {
    require_docker
    say "Rebuilding from scratch (no layer cache)"
    compose build --no-cache --pull ui
    cmd_restart
}

cmd_shell() {
    require_docker
    say "Interactive shell inside the app container"
    compose exec ui bash
}

cmd_cli() {
    require_docker
    [ "$#" -gt 0 ] || die "usage: ./scripts/project.sh cli <deck.pdf> [url] [--out ...]"
    compose run --rm cli "$@"
}

cmd_clean() {
    require_docker
    say "Removing this project's containers, volumes and image"
    compose down --volumes --remove-orphans
    docker image rm "$IMAGE" 2>/dev/null || true
    ok "nothing of this project is left on the machine (the source tree is untouched)"
}

cmd_autostart() {
    local action="${1:-status}"
    command -v systemctl >/dev/null 2>&1 || die "systemctl is not available on this machine"
    case "$action" in
        off)
            say "Disabling the Docker daemon at boot"
            sudo systemctl disable --now docker || die "could not disable docker (needs sudo)"
            ok "docker will not start on reboot; containers cannot start either" ;;
        on)
            say "Enabling the Docker daemon at boot"
            sudo systemctl enable --now docker || die "could not enable docker (needs sudo)"
            ok "the daemon starts on reboot, but this project's containers still do not" ;;
        status)
            printf '  docker daemon enabled at boot: %s\n' "$(systemctl is-enabled docker 2>/dev/null || echo unknown)"
            printf '  project containers restart policy: no\n' ;;
        *) die "usage: ./scripts/project.sh autostart [on|off|status]" ;;
    esac
}

usage() {
    cat <<EOF
${BOLD}DueDil.Agent — container control${RESET}

  ${BOLD}./scripts/project.sh start${RESET}              build if needed, start, wait until healthy
  ${BOLD}./scripts/project.sh stop${RESET}               stop and remove the containers (data kept)
  ${BOLD}./scripts/project.sh restart${RESET}            stop, then start
  ${BOLD}./scripts/project.sh status${RESET}             what is running, health, auto-start settings
  ${BOLD}./scripts/project.sh logs${RESET}               follow the application log

  ./scripts/project.sh build                build the image
  ./scripts/project.sh rebuild              build without cache, then restart
  ./scripts/project.sh shell                shell inside the running container
  ./scripts/project.sh cli <deck> [url]     run the CLI once, in a throwaway container
  ./scripts/project.sh clean                remove containers, volumes and image
  ./scripts/project.sh autostart [on|off]   control the Docker daemon's boot behaviour

  ./scripts/project.sh instance             show this checkout's compose name and port
  ./scripts/project.sh instance auto        derive both from your username (shared server)
  ./scripts/project.sh instance <name> [port]   set them explicitly

The app is served at http://localhost:${DUEDIL_PORT:-8501} while started.
Nothing starts automatically — including after a reboot.
EOF
}

main() {
    local command="${1:-}"
    [ "$#" -gt 0 ] && shift || true
    case "$command" in
        start)     cmd_start "$@" ;;
        stop)      cmd_stop "$@" ;;
        restart)   cmd_restart "$@" ;;
        status|ps) cmd_status "$@" ;;
        logs)      cmd_logs "$@" ;;
        build)     cmd_build "$@" ;;
        rebuild)   cmd_rebuild "$@" ;;
        shell)     cmd_shell "$@" ;;
        cli)       cmd_cli "$@" ;;
        clean)     cmd_clean "$@" ;;
        instance)  cmd_instance "$@" ;;
        autostart) cmd_autostart "$@" ;;
        ""|-h|--help|help) usage ;;
        *) die "unknown command '$command' (try --help)" ;;
    esac
}

main "$@"
