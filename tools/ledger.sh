#!/bin/bash
# Wrapper for the systemd timer: the ledger itself is tools/ledger.py (runs on every OS).
set -e
cd "$(dirname "$0")/.."
exec python3 tools/ledger.py "$@"
