#!/usr/bin/env bash
# One-time setup (Fraser's Mac): trigger the Daily Card price scans at 07:15 and 16:15 UK time, every day.
#  - asks for a GitHub fine-grained token (hidden) limited to this repository with "Actions: Read and write";
#    stores it in ~/.config/prediction-markets-lab/github_token (readable only by you; never committed)
#  - installs LaunchAgent com.prediction-markets-lab.dispatch (if the Mac is asleep at those times it runs on wake;
#    if the Mac is off, GitHub's own schedule still runs later as a fallback)
#  - log: data/private/dispatch.log (HTTP 204 = accepted)
# Remove later with:  scripts/setup_dispatcher_mac.sh --uninstall
set -euo pipefail
LABEL="com.prediction-markets-lab.dispatch"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
KEYDIR="$HOME/.config/prediction-markets-lab"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
if [ "${1:-}" = "--uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST" "$KEYDIR/github_token"
  echo "Removed the dispatcher and the stored token."; exit 0
fi
read -r -s -p "Paste your GitHub fine-grained token (hidden), then press Enter: " TOK; echo
[ -n "$TOK" ] || { echo "No token entered -- nothing installed."; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOK" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/frazwil19-gif/prediction-markets-lab/actions/workflows")
[ "$code" = "200" ] || { echo "GitHub rejected the token (HTTP $code). Check it is for this repository with Actions: Read and write."; exit 1; }
mkdir -p "$KEYDIR" "$REPO/data/private" "$HOME/Library/LaunchAgents"
umask 077; printf '%s' "$TOK" > "$KEYDIR/github_token"; chmod 600 "$KEYDIR/github_token"; unset TOK
chmod +x "$REPO/scripts/dispatch_workflows.sh"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$REPO/scripts/dispatch_workflows.sh</string></array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>StartCalendarInterval</key><array>
    <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>15</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$REPO/data/private/dispatch.log</string>
  <key>StandardErrorPath</key><string>$REPO/data/private/dispatch.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed: price scans will be triggered at 07:15 and 16:15 UK time (or on wake)."
echo "Log: $REPO/data/private/dispatch.log  (204 = accepted by GitHub)"
