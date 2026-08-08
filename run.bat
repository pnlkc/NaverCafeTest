@echo off
chcp 65001 > nul
title Naver Cafe Auto Manager Unified Server Launcher

echo ============================================================
echo  Naver Cafe Auto Manager Launcher (with Watchdog)
echo ============================================================
echo.
echo [Launch] Starting servers and monitoring process...
echo.

.\venv\Scripts\python.exe watchdog.py

echo.
echo [Exit] Program has terminated.
pause
