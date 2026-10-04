@echo off
title AnonGrief Server Launcher [Python]
color 0b

echo =======================================================
echo          ANONGRIEF REVOLUTION // LAUNCHER
echo =======================================================
echo.
echo [*] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0c
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

echo [*] Starting AnonGrief server on http://localhost:7777...
echo [*] Opening browser...
start http://localhost:7777
echo [*] Press Ctrl+C in this window to stop the server.
echo =======================================================
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 7777

pause
