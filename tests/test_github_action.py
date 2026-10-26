"""Guard the composite action, the entrypoint and the workflows that demonstrate it.

An action is a public interface: consumers write `uses: SergeyGer/duedil-agent@v…` and rely on
the input names, the outputs and the fact that the action's dependencies are pinned. These tests
fail when that interface drifts or when a workflow step forgets a pin.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTION = REPO_ROOT / "action.yml"
ENTRYPOINT = REPO_ROOT / "scripts" / "action_entrypoint.sh"
DEMO_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "due-diligence-demo.yml"
EXAMPLE_WORKFLOW = REPO_ROOT / "examples" / "github-action.yml"

SHA_RE = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def _action() -> dict:
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


def test_action_metadata_is_complete():
    action = _action()
    assert action["name"]
    assert action["description"]
    assert action["runs"]["using"] == "composite"


def test_every_input_is_documented():
    inputs = _action()["inputs"]
    assert "deck" in inputs
    assert inputs["deck"]["required"] is True
    for name, spec in inputs.items():
        assert spec.get("description"), f"input {name!r} has no description"


def test_every_output_is_documented_and_wired():
    outputs = _action()["outputs"]
    assert {"memo", "markdown", "comment", "state", "recommendation"} <= set(outputs)
    for name, spec in outputs.items():
        assert spec.get("description"), f"output {name!r} has no description"
        assert "steps.run.outputs" in spec["value"], f"output {name!r} is not wired to the run step"


def test_action_uses_are_sha_pinned():
    action = _action()
    for step in action["runs"]["steps"]:
        uses = step.get("uses")
        if not uses:
            continue
        assert SHA_RE.match(uses), f"{uses!r} is not pinned to a commit SHA"
        raw = ACTION.read_text(encoding="utf-8")
        assert f"{uses}  # v" in raw, f"{uses!r} has no version comment next to the pin"


def test_entrypoint_is_executable_and_strict():
    assert ENTRYPOINT.is_file()
    assert ENTRYPOINT.stat().st_mode & 0o111, "the entrypoint must be executable"
    text = ENTRYPOINT.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "INPUT_DECK" in text


def test_entrypoint_reads_every_input_the_action_passes():
    """The action and the script must agree on the INPUT_* names, or inputs silently vanish."""

    action_env = _action()["runs"]["steps"][-1].get("env") or {}
    script = ENTRYPOINT.read_text(encoding="utf-8")
    for env_name in action_env:
        assert env_name in script, f"{env_name} is passed by action.yml but never read"


@pytest.mark.parametrize("workflow", [DEMO_WORKFLOW, EXAMPLE_WORKFLOW])
def test_workflows_are_valid_yaml_with_pinned_actions(workflow: Path):
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    raw = workflow.read_text(encoding="utf-8")

    for job in data["jobs"].values():
        for step in job["steps"]:
            uses = step.get("uses")
            if not uses:
                continue
            if uses.startswith("./") or uses.startswith("SergeyGer/duedil-agent@"):
                continue
            assert SHA_RE.match(uses), f"{workflow.name}: {uses!r} is not pinned"
            assert f"{uses}  # v" in raw


def test_demo_workflow_actually_posts_a_comment():
    text = DEMO_WORKFLOW.read_text(encoding="utf-8")
    assert "uses: ./" in text
    assert "gh pr comment" in text
    assert "--body-file" in text
    assert "pull-requests: write" in text


def test_example_workflow_points_at_this_repository():
    text = EXAMPLE_WORKFLOW.read_text(encoding="utf-8")
    assert "SergeyGer/duedil-agent@" in text
    assert "gh pr comment" in text
