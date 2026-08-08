@echo off
chcp 65001 >nul
title Naver Cafe Data Cleaner Utility

echo ============================================================
echo   Naver Cafe Data Cleaner Utility (System Wide Reset)
echo ============================================================
echo.
echo  [Warning] This will wipe all news, member, logs, and alert tables.
echo.

.\venv\Scripts\python.exe backend\clean_data.py

echo.
echo  [Done] System data cleanup finished successfully.
timeout /t 2 >nul
exit /b 0
