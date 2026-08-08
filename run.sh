#!/bin/bash
echo "============================================================"
echo "  Naver Cafe Auto Manager System Launcher (macOS/Linux)"
echo "============================================================"
echo ""
echo "  [Info] Starting Backend Server and Dashboard Web App..."
echo ""

if [ -d "venv" ]; then
    ./venv/bin/python watchdog.py
else
    python3 watchdog.py
fi
