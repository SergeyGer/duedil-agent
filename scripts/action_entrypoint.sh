#!/usr/bin/env bash
# Entry point for the DueDil.Agent composite action (`action.yml`).
#
# The action's own checkout supplies the application code; the caller's workspace supplies the
# deck and receives the artefacts. Set -euo pipefail so a failed analysis fails the job instead of
# publishing an empty comment.
set -euo pipefail

deck="${INPUT_DECK:?the 'deck' input is required}"
url="${INPUT_URL:-}"
output_dir="${INPUT_OUTPUT_DIR:-duedil-output}"
model="${INPUT_MODEL:-}"
offline_input="${INPUT_OFFLINE:-auto}"
workspace="${GITHUB_WORKSPACE:-$(pwd)}"
action_path="${GITHUB_ACTION_PATH:?this script is meant to run from the composite action}"

cd "$workspace"

if [[ ! -f "$deck" ]]; then
  echo "::error title=Deck not found::'$deck' does not exist in the workspace. Paths are relative to the repository root."
  exit 1
fi

# `auto` keeps the action usable in a repository with no secrets: the rule-based agents read the
# deck without a model, and the memo says so instead of pretending an LLM ran.
offline="false"
case "$offline_input" in
  true) offline="true" ;;
  false) offline="false" ;;
  auto)
    if [[ -n "${OPENAI_API_KEY:-}" || -n "${ANTHROPIC_API_KEY:-}" ]]; then
      offline="false"
    else
      offline="true"
    fi
    ;;
  *)
    echo "::error title=Invalid offline input::expected auto, true or false, got '$offline_input'."
    exit 1
    ;;
esac

# Accept both a workspace-relative directory (the common case) and an absolute one.
case "$output_dir" in
  /*) out_abs="$output_dir" ;;
  *) out_abs="$workspace/$output_dir" ;;
esac
mkdir -p "$out_abs"

pdf="$out_abs/memo.pdf"
markdown="$out_abs/memo.md"
state_file="$out_abs/state.json"
comment_file="$out_abs/comment.md"

args=(python -m app.cli "$deck" "$url"
      --out "$pdf" --md "$markdown" --json "$state_file" --comment-file "$comment_file")
[[ -n "$model" && "$offline" == "false" ]] && args+=(--model "$model")
[[ "$offline" == "true" ]] && args+=(--offline)

echo "DueDil.Agent: $deck (offline=$offline)"
export PYTHONPATH="${action_path}${PYTHONPATH:+:$PYTHONPATH}"
"${args[@]}"

# The pipeline exits non-zero only when it produced nothing; reaching this point means all four
# files exist. The paths are already absolute, so the workflow can use them from any directory.
state_abs="$state_file"
comment_abs="$comment_file"

recommendation="$(python - "$state_abs" <<'PY'
import json
import sys
from pathlib import Path

from app.comment import recommendation_of

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(recommendation_of(state))
PY
)"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "memo=$pdf"
    echo "markdown=$markdown"
    echo "state=$state_abs"
    echo "comment=$comment_abs"
    echo "recommendation=$recommendation"
  } >> "$GITHUB_OUTPUT"
fi

# The same summary in the run's job summary, so the result is visible without opening the PR.
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat "$comment_abs" >> "$GITHUB_STEP_SUMMARY"
fi

echo "Recommendation: $recommendation"
echo "Comment: $comment_abs"
