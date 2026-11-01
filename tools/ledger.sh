#!/bin/bash
# Monthly ledger: what this machine actually ran, from the local Claude Code transcripts
# (tools/usage_scan.py): subagent calls by type, tokens and catalog-priced cost by model.
# Writes ledger/usage-<date>.md; with --commit it also commits and pushes it.
# tools/install_ledger_timer.sh installs a systemd user timer that runs it monthly (your call).
set -e
cd "$(dirname "$0")/.."
mkdir -p ledger
f=ledger/usage-$(date +%Y-%m-%d).md
{ echo "# Usage ledger, $(date +%Y-%m-%d)"; echo; echo "Claude Code $(claude --version 2>/dev/null | head -1). Catalog-equivalent prices (catalog/models.json); on a subscription they measure rate-limit headroom, not a bill."; echo; echo '```'; python3 tools/usage_scan.py; echo '```'; } > "$f"
echo "wrote $f"
if [ "$1" = "--commit" ]; then
  git add "$f" && git commit -qm "ledger: usage $(date +%Y-%m-%d)" && git push -q && echo committed
fi
