#!/usr/bin/env bash
# Refresh the stats card from your own machine, using your `gh` login.
# Handy while GitHub Actions is unavailable for this account.
set -euo pipefail
cd "$(dirname "$0")/.."

git pull -q --rebase
data=$(mktemp)
trap 'rm -f "$data"' EXIT
gh api graphql -F query=@scripts/query.graphql > "$data"
python3 scripts/gen.py --data "$data"

git add assets/stats.svg
if git diff --cached --quiet; then
  echo "Stats card is already up to date."
  exit 0
fi
git commit -q -m "chore: refresh stats card"
git push -q
echo "Stats card refreshed and pushed."
