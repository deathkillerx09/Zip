@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==========================================
echo            AI MONEY TOWN
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating the Python environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto :error
)

echo Checking required Python packages...
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 goto :error

if not exist "data" mkdir "data"
if not exist "workspace" mkdir "workspace"
if exist "data\town.db" if not exist "data\town.db.prelaunch.bak" (
    echo Creating a one-time backup of your town database...
    copy /y "data\town.db" "data\town.db.prelaunch.bak" >nul
    if errorlevel 1 goto :error
)

if not exist ".owner-token" (
    ".venv\Scripts\python.exe" -c "from pathlib import Path; import uuid; Path('.owner-token').write_text(uuid.uuid4().hex + uuid.uuid4().hex, encoding='utf-8')"
    if errorlevel 1 goto :error
)
for /f "usebackq delims=" %%T in (".owner-token") do set "AI_MONEY_TOWN_OWNER_TOKEN=%%T"
set "AI_MONEY_TOWN_DB=%CD%\data\town.db"
set "AI_MONEY_TOWN_WORKSPACE=%CD%\workspace"
set "OLLAMA_BASE_URL=http://127.0.0.1:11434"
set "OLLAMA_TIMEOUT_SECONDS=100"
set "OLLAMA_CHAT_MODEL=qwen3.5:0.8b"
rem Use the quick model for short idea batches and the stronger model for worker research/build planning.
set "OLLAMA_IDEA_MODEL=qwen3.5:0.8b"
set "OLLAMA_WORKER_MODEL=qwen3:4b"
rem Product files are written by the builder. Any value that is not installed falls back
rem to OLLAMA_WORKER_MODEL automatically, so this line is safe to leave as is.
set "OLLAMA_MODEL_PRODUCT=qwen3:4b"
set "OLLAMA_TASK_TIMEOUT_SECONDS=110"
set "OLLAMA_NUM_CTX=1024"
set "OLLAMA_NUM_PREDICT=64"
set "AI_MONEY_TOWN_SCHEDULER_SECONDS=20"
set "AI_MONEY_TOWN_SCHEDULER_START_DELAY_SECONDS=5"
set "AI_MONEY_TOWN_INITIAL_IDEA_DELAY_SECONDS=30"
rem Target 50 idea candidates/hour: 10 compact ideas every 12 minutes.
rem Actual throughput depends on local Ollama speed, available RAM and model output quality.
set "AI_MONEY_TOWN_IDEA_TARGET_PER_HOUR=50"
set "AI_MONEY_TOWN_IDEA_BATCH_SIZE=10"
set "AI_MONEY_TOWN_IDEA_INTERVAL_SECONDS=720"
rem Worker safety limits: one model call at a time, three attempts per task, then a
rem recorded failure instead of an endless retry. Stuck tasks are recovered after 15 min.
set "AI_MONEY_TOWN_TASK_CONCURRENCY=1"
set "AI_MONEY_TOWN_TASK_MAX_ATTEMPTS=3"
set "AI_MONEY_TOWN_STALE_TASK_SECONDS=900"
set "AI_MONEY_TOWN_RATE_LIMIT_PER_MINUTE=240"

echo Checking the local Ollama service...
curl.exe -fsS http://127.0.0.1:11434/api/tags >nul 2>nul
if errorlevel 1 (
    where ollama >nul 2>nul
    if not errorlevel 1 (
        echo Ollama is installed but not responding. Starting it now...
        start "Ollama local service" /min cmd /c "ollama serve"
        timeout /t 4 /nobreak >nul
    ) else (
        echo Ollama was not found. The town will open, but AI chat and workers will remain offline.
    )
) else (
    echo Ollama is online.
)

echo.
echo Starting the local server at http://127.0.0.1:8000
echo Your private owner token is stored in .owner-token. Keep that file private.
echo Paste it into the Treasury panel to unlock owner actions (approvals, ledger, product builds).
echo Press Ctrl+C in this window to stop AI Money Town.
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000'"
".venv\Scripts\python.exe" -m uvicorn app.server:app --app-dir backend --host 127.0.0.1 --port 8000
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo AI Money Town could not start. Check the error messages above.
pause
exit /b 1

:check_ollama
for /l %%I in (1,1,15) do (
    curl.exe -fsS http://127.0.0.1:11434/api/tags >nul 2>nul
    if not errorlevel 1 exit /b 0
    timeout /t 1 /nobreak >nul
)
exit /b 1
