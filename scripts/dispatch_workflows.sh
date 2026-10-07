#!/usr/bin/env bash
# Trigger the price scans at fixed UK times from Fraser's Mac (GitHub's own cron runs 3-9 h late on this repo).
# Called by the LaunchAgent installed by scripts/setup_dispatcher_mac.sh. Morning (before 12:00 local): football daily
# scan + tennis board; afternoon: tennis board. Both workflows rebuild reports/daily_card_v1.md at the end.
# The GitHub cron stays as a fallback; scripts/recent_run_guard.py stops a late duplicate from paying twice.
set -uo pipefail
TOKEN_FILE="$HOME/.config/prediction-markets-lab/github_token"
REPO_SLUG="frazwil19-gif/prediction-markets-lab"
LOG="$(cd "$(dirname "$0")/.." && pwd)/data/private/dispatch.log"
mkdir -p "$(dirname "$LOG")"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
[ -r "$TOKEN_FILE" ] || { echo "$(ts) no token file -- run scripts/setup_dispatcher_mac.sh" >> "$LOG"; exit 1; }
TOKEN="$(cat "$TOKEN_FILE")"
dispatch() {  # $1 workflow file, $2 JSON inputs
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO_SLUG/actions/workflows/$1/dispatches" \
    -d "{\"ref\":\"master\",\"inputs\":$2}")
  echo "$(ts) dispatch $1 -> HTTP $code" >> "$LOG"   # 204 = accepted
}
HOUR=$(date +%H)
if [ "$HOUR" -lt 12 ]; then
  dispatch daily_scan.yml '{"run_label":""}'
  sleep 5
fi
dispatch tennis_prediction_board.yml '{"mode":"board"}'
