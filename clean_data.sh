#!/bin/bash
echo "============================================================"
echo "  Naver Cafe Data Cleaner Utility (macOS / Linux)"
echo "============================================================"
echo ""
echo "  [Warning] This will wipe all news, member, logs, and alert tables."
echo ""

if [ -d "venv" ]; then
    ./venv/bin/python backend/clean_data.py
else
    python3 backend/clean_data.py
fi

echo ""
echo "  [Done] System data cleanup finished successfully."
