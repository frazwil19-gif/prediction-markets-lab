#!/usr/bin/env bash
# One-time setup (Fraser's Mac, after scripts/setup_dispatcher_mac.sh): trigger the CLV capture every 15 minutes while
# the Mac is awake. Uses the GitHub token already stored by setup_dispatcher_mac.sh (nothing new to paste).
# Remove later with:  scripts/setup_clv_dispatcher_mac.sh --uninstall
set -euo pipefail
LABEL="com.prediction-markets-lab.clv"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
if [ "${1:-}" = "--uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true; rm -f "$PLIST"; echo "Removed the CLV dispatcher."; exit 0
fi
[ -r "$HOME/.config/prediction-markets-lab/github_token" ] || { echo "Run scripts/setup_dispatcher_mac.sh first (stores the token)."; exit 1; }
chmod +x "$REPO/scripts/dispatch_clv.sh"
mkdir -p "$REPO/data/private" "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$REPO/scripts/dispatch_clv.sh</string></array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>StartInterval</key><integer>900</integer>
  <key>StandardOutPath</key><string>$REPO/data/private/dispatch_clv.log</string>
  <key>StandardErrorPath</key><string>$REPO/data/private/dispatch_clv.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
"$REPO/scripts/dispatch_clv.sh"; tail -1 "$REPO/data/private/dispatch_clv.log"
echo "Installed: CLV capture triggered every 15 minutes while this Mac is awake (204 = accepted)."
