#!/usr/bin/env bash
#
# Publish docs/wiki/*.md to the repository's GitHub wiki.
#
# The wiki is a separate git repository (duedil-agent.wiki.git), so the sources are
# versioned here with the code and pushed there with this script. GitHub renders
# `_Sidebar.md` as the navigation sidebar and `Home.md` as the landing page.
#
# Usage:
#   scripts/publish_wiki.sh                 # clone/refresh into .wiki and push
#   WIKI_DIR=/tmp/w scripts/publish_wiki.sh # use another scratch directory
#
# Requires push access to <remote>.wiki.git (a PAT with Contents: write works).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$REPO_ROOT/docs/wiki"
WIKI_DIR="${WIKI_DIR:-$REPO_ROOT/.wiki}"

REMOTE="$(git -C "$REPO_ROOT" remote get-url origin)"
WIKI_REMOTE="${REMOTE%.git}.wiki.git"

if [ ! -d "$SRC_DIR" ]; then
    echo "error: $SRC_DIR not found" >&2
    exit 1
fi

echo "wiki remote : $WIKI_REMOTE"
echo "sources     : $SRC_DIR"
echo "scratch dir : $WIKI_DIR"

if [ -d "$WIKI_DIR/.git" ]; then
    git -C "$WIKI_DIR" fetch --quiet origin
    git -C "$WIKI_DIR" reset --hard --quiet origin/master
else
    rm -rf "$WIKI_DIR"
    git clone --quiet "$WIKI_REMOTE" "$WIKI_DIR"
fi

# Mirror the sources, including deletions, then normalise file modes.
find "$WIKI_DIR" -maxdepth 1 -name '*.md' -delete
cp "$SRC_DIR"/*.md "$WIKI_DIR"/
chmod 644 "$WIKI_DIR"/*.md

cd "$WIKI_DIR"
if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
    echo "wiki is already up to date"
    exit 0
fi

git add -A
git -c user.name="${GIT_AUTHOR_NAME:-$(git -C "$REPO_ROOT" config user.name)}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-$(git -C "$REPO_ROOT" config user.email)}" \
    commit --quiet -m "docs(wiki): sync from docs/wiki at $(git -C "$REPO_ROOT" rev-parse --short HEAD)"
git push --quiet origin master

echo "published $(ls -1 "$SRC_DIR"/*.md | wc -l) pages"
