"""Consistency checks for the generated Run & Stop guide.

The guide is written by hand and quotes real infrastructure: an SSH config, key paths,
scripts, Make targets and compose variables. Every one of those is a reference that can
silently go stale — the document would tell a reader to run `ssh <something>` that does
not exist in their config, or `./scripts/gone.sh`.

These tests flatten the Russian guide to text and assert that everything it refers to
either exists in the repository or is defined inside the document itself.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = REPO_ROOT / "scripts" / "make_run_stop_doc.py"

#: The SSH config that is actually in use. The document must quote it verbatim, and the
#: commands in it must use these names — not aliases or key files that do not exist.
EXPECTED_SSH_CONFIG = [
    "Host Hetzner 188.245.2.148",
    "HostName 188.245.2.148",
    "User root",
    "IdentityFile ~/.ssh/id_ed25519",
    "IdentitiesOnly yes",
    "AddKeysToAgent yes",
    "ServerAliveInterval 30",
    "ServerAliveCountMax 4",
    "TCPKeepAlive yes",
    "PasswordAuthentication no",
    "KbdInteractiveAuthentication no",
    "PreferredAuthentications publickey",
]

#: Paths under ~/.ssh that may legitimately be mentioned.
ALLOWED_SSH_FILES = {"id_ed25519", "config", "authorized_keys"}

#: Hosts that need no `Host` entry in the SSH config.
ALLOWED_BARE_HOSTS = {"188.245.2.148", "127.0.0.1", "localhost"}


def _load_ru_content():
    """Import the guide content without importing the renderer's dependencies at import time."""

    name = "make_run_stop_doc_under_test"
    spec = importlib.util.spec_from_file_location(name, GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # `@dataclass` resolves the class's module through sys.modules, so register it first.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.RU


def _flatten(value) -> list[str]:
    """Collect every string inside the block structure, preserving nothing but the text."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(_flatten(item))
        return out
    return []


def guide_text() -> str:
    return "\n".join(_flatten(_load_ru_content().blocks))


# --- SSH ---------------------------------------------------------------------
def _ssh_config_block() -> list[str]:
    """The code block that holds the config, compared line by line.

    Searching the whole document for these lines is not enough: the bullets right below
    the block also name the directives, so a dropped config line would be masked.
    """

    for block in _load_ru_content().blocks:
        if (
            block[0] == "code"
            and "Host Hetzner" in block[1]
            and "PreferredAuthentications" in block[1]
        ):
            return [line.strip() for line in block[1].splitlines() if line.strip()]
    raise AssertionError("the guide has no code block containing the SSH config")


def test_the_guide_quotes_the_real_ssh_config_line_by_line():
    """Inserting the config is not enough: a dropped line would mislead the reader."""

    block = _ssh_config_block()
    assert block == EXPECTED_SSH_CONFIG, (
        "the SSH config in the guide differs from the one in use:\n"
        f"  only in guide: {sorted(set(block) - set(EXPECTED_SSH_CONFIG))}\n"
        f"  only expected: {sorted(set(EXPECTED_SSH_CONFIG) - set(block))}"
    )


def _ssh_command_targets(text: str) -> set[str]:
    """Host part of every real `ssh ...` command line in the guide.

    Only lines that start with `ssh ` are commands; prose that happens to contain the
    word is ignored. Options taking a value (`-L`, `-i`, `-o`, `-p`, `-J`) are skipped
    together with their argument.
    """

    takes_value = {"-L", "-R", "-i", "-o", "-p", "-J", "-D", "-l"}
    targets: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("ssh "):
            continue
        tokens = line.split()
        index = 1
        target = None
        while index < len(tokens):
            token = tokens[index]
            if token in takes_value:
                index += 2
                continue
            if token.startswith("-"):
                index += 1
                continue
            target = token
            break
        if not target:
            continue  # e.g. `ssh -V`
        host = target.split("@")[-1].rstrip(".,;:")
        targets.add(host)
    return targets


def test_every_ssh_target_exists_in_the_config():
    text = guide_text()
    aliases = set(re.findall(r"^Host\s+(\S+)", text, re.MULTILINE))

    unknown = {
        host
        for host in _ssh_command_targets(text)
        if host not in aliases and host not in ALLOWED_BARE_HOSTS
    }
    assert not unknown, f"the guide connects to hosts that no `Host` block defines: {unknown}"


def test_every_ssh_key_path_exists_in_the_config():
    # Normalise Windows paths first, so `$env:USERPROFILE\.ssh\x` and `~/.ssh/x` compare.
    text = guide_text().replace("\\\\", "/").replace("\\", "/")
    names = {
        # A prose sentence ends with a full stop, which is not part of the file name.
        name.removesuffix(".pub").rstrip(".")
        for name in re.findall(r"(?:~|\$env:USERPROFILE)/\.ssh/([A-Za-z0-9._-]+)", text)
    }
    unknown = names - ALLOWED_SSH_FILES
    assert not unknown, f"the guide mentions key files that do not exist: {unknown}"
    assert names, "the regex found no key paths at all"


def test_the_old_placeholder_identity_is_gone():
    """Regression guard: the first version invented `Host duedil` and `~/.ssh/duedil`."""

    text = guide_text()
    assert "Host duedil" not in text
    assert "~/.ssh/duedil" not in text
    assert "ssh duedil" not in text


# --- scripts, make targets, compose variables --------------------------------
def test_every_referenced_script_exists():
    text = guide_text()
    referenced = set(re.findall(r"\./?scripts/([A-Za-z0-9_.-]+\.(?:sh|ps1))", text))
    missing = [name for name in referenced if not (REPO_ROOT / "scripts" / name).is_file()]
    assert not missing, f"the guide references missing scripts: {missing}"


def test_every_referenced_make_target_exists():
    text = guide_text()
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    defined = set(re.findall(r"^([A-Za-z0-9_.-]+):", makefile, re.MULTILINE))
    referenced = set(re.findall(r"\bmake\s+([a-z][a-z0-9-]*)", text))
    unknown = referenced - defined
    assert not unknown, f"the guide references missing make targets: {unknown}"


def test_every_referenced_compose_variable_is_real():
    text = guide_text()
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    referenced = set(re.findall(r"\b(DUEDIL_[A-Z_]+|COMPOSE_PROJECT_NAME)\b", text))
    unknown = {name for name in referenced if name not in compose}
    assert not unknown, (
        f"the guide names compose variables that the compose file ignores: {unknown}"
    )


def test_the_guide_mentions_the_current_server_address():
    text = guide_text()
    assert "188.245.2.148" in text
    assert "текущий реальный сервер" in text
