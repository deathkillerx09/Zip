@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo      STOPPING AI MONEY TOWN
echo ==========================================
echo.

set FOUND=0
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Stopping server process %%P on port 8000...
    taskkill /PID %%P /T /F >nul 2>nul
    set FOUND=1
)

if "!FOUND!"=="1" (
    echo AI Money Town has stopped. Your database and generated product files are untouched.
) else (
    echo Nothing was listening on port 8000. The town may already be stopped.
    echo If a black server window is still open, press Ctrl+C in that window.
)

echo.
pause
exit /b 0
