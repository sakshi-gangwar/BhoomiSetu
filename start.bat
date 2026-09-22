@echo off
cd /d "%~dp0"

echo Starting BhoomiSetu...
start "BhoomiSetu Server" cmd /k "py -3 main.py"

timeout /t 5 /nobreak >nul

start "" "http://127.0.0.1:8000"