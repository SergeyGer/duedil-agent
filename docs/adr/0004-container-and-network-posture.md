# 0004 — Non-root container, loopback-only publishing

## Status

Accepted


## Context

The project runs in several places at once: a laptop, a shared Linux server that hosts other
projects, and a public demo. A container that listens on `0.0.0.0` and runs as root is the
default for many Dockerfiles, and it means one misconfiguration exposes an app that holds API
keys — and on a shared server, two developers immediately fight over port 8501 and the container
name.

## Decision

* The image runs as a dedicated non-root user (`duedil`, uid 10001); only `/app/data` is writable.
* The compose file publishes **`${DUEDIL_BIND:-127.0.0.1}:${DUEDIL_PORT:-8501}:8501`** — loopback
  by default, port configurable per developer, and no fixed `container_name`, so a second
  checkout on the same host is possible.
* `restart: "no"` for both services: nothing comes back after a reboot or a daemon restart.
* Remote access is expected through an SSH tunnel or VS Code port forwarding, not through an open
  port.

## Consequences

* The app is not reachable from the network until someone deliberately sets
  `DUEDIL_BIND=0.0.0.0`, which is a visible act in a shell, not a forgotten default.
* The demo and the server behave the same way, so a screenshot is not lying about the setup.
* Local convenience costs one tunnel command (or one VS Code port-forward click).
* Health checks run inside the container against `127.0.0.1`, so they keep working in both modes.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
