"""Guards for the container-control scripts and the dev container configuration.

These files are easy to break silently: a script and its Windows twin can drift, a
Makefile target can point at a command that no longer exists, and — the mistake this
module exists for — someone can reintroduce an auto-restart policy that makes the stack
come back after a server reboot, which is exactly what the project must not do.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE = REPO_ROOT / "docker-compose.yml"
BASH = REPO_ROOT / "scripts" / "project.sh"
POWERSHELL = REPO_ROOT / "scripts" / "project.ps1"
MAKEFILE = REPO_ROOT / "Makefile"
DEVCONTAINER = REPO_ROOT / ".devcontainer" / "devcontainer.json"

#: Commands both scripts must offer, with the same names.
COMMANDS = [
    "start",
    "stop",
    "restart",
    "status",
    "logs",
    "build",
    "rebuild",
    "shell",
    "cli",
    "clean",
]


def _compose_text() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def test_services_never_start_by_themselves():
    """`restart: no` is load-bearing: it is what keeps a reboot from starting the stack."""

    text = _compose_text()
    # Only real directives: a comment may mention the policy without setting it.
    policies = re.findall(r"^\s+restart:\s*(\S.*?)\s*$", text, re.MULTILINE)
    assert policies, "no restart policy found in docker-compose.yml"
    for policy in policies:
        assert policy in {'"no"', "'no'", "no"}, (
            f"restart policy {policy!r} lets the stack come back on its own; "
            'the project requires restart: "no"'
        )
    # The two alternatives that Docker brings back when the daemon starts, in a directive.
    assert not re.search(r"^\s+restart:\s*(always|unless-stopped)", text, re.MULTILINE)


def test_compose_project_name_is_pinned():
    """A fixed name keeps this stack's containers, network and volumes separate."""

    assert "name: duedil-agent" in _compose_text()


def test_the_cli_service_stays_profile_gated():
    """`docker compose up` must not start a one-off CLI runner."""

    text = _compose_text()
    cli_block = text.split("  cli:", 1)[1]
    assert 'profiles: ["cli"]' in cli_block


def test_both_scripts_offer_the_same_commands():
    bash = BASH.read_text(encoding="utf-8")
    powershell = POWERSHELL.read_text(encoding="utf-8")

    for command in COMMANDS:
        assert re.search(rf"^\s*{command}\)", bash, re.MULTILINE), f"project.sh has no '{command}'"
        assert f'"{command}"' in powershell, f"project.ps1 has no '{command}'"


def test_wrappers_and_make_targets_forward_to_the_script():
    for wrapper, verb in ((REPO_ROOT / "start.sh", "start"), (REPO_ROOT / "stop.sh", "stop")):
        text = wrapper.read_text(encoding="utf-8")
        assert f'exec "$BASE/scripts/project.sh" {verb}' in text, (
            f"{wrapper.name} does not forward '{verb}'"
        )

    makefile = MAKEFILE.read_text(encoding="utf-8")
    for target, command in (
        ("up", "project.sh start"),
        ("down", "project.sh stop"),
        ("status", "project.sh status"),
        ("logs", "project.sh logs"),
        ("shell", "project.sh shell"),
    ):
        block = makefile.split(f"\n{target}:", 1)
        assert len(block) == 2, f"the Makefile has no '{target}' target"
        assert command in block[1].split("\n\n", 1)[0], f"'{target}' does not call {command}"


def test_windows_wrappers_exist_and_call_powershell():
    for name, verb in (("start.cmd", "start"), ("stop.cmd", "stop")):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        assert "project.ps1" in text, f"{name} does not call the PowerShell script"
        assert f" {verb}" in text, f"{name} does not pass '{verb}'"


def test_devcontainer_uses_the_compose_service():
    raw = DEVCONTAINER.read_text(encoding="utf-8")
    config = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.MULTILINE))

    assert config["dockerComposeFile"] == ["../docker-compose.yml"]
    assert config["service"] == "ui", "the dev container must attach to the deployed service"
    assert config["workspaceFolder"] == "/app"
    assert config["overrideCommand"] is False, "the service has to keep its own command"
    assert config["shutdownAction"] == "stopCompose", "closing VS Code must stop the stack"
    assert 8501 in config["forwardPorts"]

    # The dev environment must not invent its own dependency set: pytest and pytest-cov
    # come from requirements.txt through the image. Only ruff is added.
    post_create = config["postCreateCommand"]
    assert "--system-site-packages" in post_create
    assert "ruff" in post_create
    assert "pytest==" not in post_create, (
        "pytest versions must stay pinned in requirements.txt only"
    )


def test_the_personal_document_is_not_committed():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "Run_Stop_Project.docx" in gitignore
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".devcontainer" in dockerignore, (
        "the dev container config is not part of the runtime image"
    )
