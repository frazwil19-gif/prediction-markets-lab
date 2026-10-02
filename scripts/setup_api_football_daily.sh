#!/usr/bin/env bash
# One-time setup (Fraser's Mac): run the API-Football acquisition automatically every morning at 07:30.
#  - asks for the API key (hidden), stores it in ~/.config/prediction-markets-lab/api_football_key (readable only by you)
#  - installs a macOS LaunchAgent (com.prediction-markets-lab.api-football); if the Mac was asleep at 07:30, it runs on wake
#  - log: data/private/api_football/daily.log (private, never committed)
# Remove later with:  scripts/setup_api_football_daily.sh --uninstall
set -euo pipefail
LABEL="com.prediction-markets-lab.api-football"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
KEYDIR="$HOME/.config/prediction-markets-lab"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
if [ "${1:-}" = "--uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST" "$KEYDIR/api_football_key"
  echo "Removed the daily job and the stored key."; exit 0
fi
PY="$(command -v python3)"
read -r -s -p "Paste your API-Football key (hidden), then press Enter: " KEY; echo
[ -n "$KEY" ] || { echo "No key entered -- nothing installed."; exit 1; }
mkdir -p "$KEYDIR" "$REPO/data/private/api_football" "$HOME/Library/LaunchAgents"
umask 077; printf '%s' "$KEY" > "$KEYDIR/api_football_key"; chmod 600 "$KEYDIR/api_football_key"; unset KEY
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$REPO/scripts/api_football_acquire.py</string></array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
  <key>StandardOutPath</key><string>$REPO/data/private/api_football/daily.log</string>
  <key>StandardErrorPath</key><string>$REPO/data/private/api_football/daily.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed: runs daily at 07:30 (or on wake). Starting today's run now in the background..."
launchctl kickstart "gui/$(id -u)/$LABEL"
echo "Progress log: $REPO/data/private/api_football/daily.log"
