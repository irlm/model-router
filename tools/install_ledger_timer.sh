#!/bin/bash
# Run tools/ledger.sh --commit on the 1st of every month at 09:00 as a systemd user timer
# (this machine has no cron). Not installed by the benchmark itself; run this by hand.
# `--remove` disables and deletes the units.
set -e
U=$HOME/.config/systemd/user; mkdir -p $U
if [ "$1" = "--remove" ]; then
  systemctl --user disable --now model-router-ledger.timer 2>/dev/null || true
  rm -f $U/model-router-ledger.service $U/model-router-ledger.timer; systemctl --user daemon-reload; echo removed; exit 0
fi
cat > $U/model-router-ledger.service <<UNIT
[Unit]
Description=model-router usage ledger (tools/ledger.sh --commit)
[Service]
Type=oneshot
WorkingDirectory=$HOME/Projects/Github/model-router
ExecStart=$HOME/Projects/Github/model-router/tools/ledger.sh --commit
UNIT
cat > $U/model-router-ledger.timer <<UNIT
[Unit]
Description=Monthly model-router usage ledger
[Timer]
OnCalendar=*-*-01 09:00:00
Persistent=true
[Install]
WantedBy=timers.target
UNIT
systemctl --user daemon-reload && systemctl --user enable --now model-router-ledger.timer && systemctl --user list-timers model-router-ledger.timer --no-pager | head -3
