#!/bin/bash
# Linux / 터미널용: ./start.sh
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
