@echo off
title Naver Cafe Auto Manager Launcher

echo ============================================================
echo   Naver Cafe Auto Manager System Launcher
echo ============================================================
echo.
echo  [Info] Starting Backend Server and Dashboard Web App...
echo.

.\venv\Scripts\python.exe watchdog.py

echo.
echo  [Exit] System terminated.
pause
