#!/usr/bin/env bash
# Startar en Road2Zero-app lokalt: ./starta_mac_linux.sh [plan|cityscenario|op]   (standard: plan)
set -euo pipefail
cd "$(dirname "$0")"
APP="${1:-plan}"
case "$APP" in plan|cityscenario|op) ;; *) echo "Okänd app: $APP. Välj plan, cityscenario eller op."; exit 1 ;; esac
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python -m streamlit run "$APP/streamlit_app.py"
