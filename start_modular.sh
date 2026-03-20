#!/usr/bin/env bash
set -euo pipefail
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5003 --log-level info
