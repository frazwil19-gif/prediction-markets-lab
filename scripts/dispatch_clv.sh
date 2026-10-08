#!/usr/bin/env bash
# Every 15 min (LaunchAgent from scripts/setup_clv_dispatcher_mac.sh): trigger the CLV capture workflow so near-close
# prices are taken 0-25 min before start (GitHub's own cron is hours late). Re-uses the token stored by
# scripts/setup_dispatcher_mac.sh. Each run with nothing due makes no paid API call.
set -uo pipefail
TOKEN_FILE="$HOME/.config/prediction-markets-lab/github_token"
REPO_SLUG="frazwil19-gif/prediction-markets-lab"
LOG="$(cd "$(dirname "$0")/.." && pwd)/data/private/dispatch_clv.log"
mkdir -p "$(dirname "$LOG")"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
[ -r "$TOKEN_FILE" ] || { echo "$(ts) no token file -- run scripts/setup_dispatcher_mac.sh first" >> "$LOG"; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $(cat "$TOKEN_FILE")" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO_SLUG/actions/workflows/clv_capture.yml/dispatches" -d '{"ref":"master"}')
echo "$(ts) dispatch clv_capture.yml -> HTTP $code" >> "$LOG"
