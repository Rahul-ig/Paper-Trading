@echo off
echo ============================================
echo   AI Trading Dashboard - Local Server
echo ============================================
echo.
echo Starting local server at http://localhost:8080
echo Press Ctrl+C to stop the server
echo.
cd /d "%~dp0dashboard"
python -m http.server 8080
