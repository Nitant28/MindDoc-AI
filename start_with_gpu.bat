@echo off
REM MindDoc AI - One-Command Startup with GPU
REM Starts Ollama serve (GPU-enabled) and backend in parallel

echo.
echo ============================================================
echo    MindDoc AI - GPU-Accelerated Startup
echo ============================================================
echo.
echo [1] Starting Ollama server on GPU...
echo     Model: gpt-oss:120b-cloud
echo     GPU: NVIDIA RTX 3050
echo.

REM Set Ollama environment variables for GPU optimization
set OLLAMA_MODEL=gpt-oss:120b-cloud
set OLLAMA_API_URL=http://127.0.0.1:11434/api/generate
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_SCHED_SPREAD=1
set OLLAMA_DEBUG=0
set OLLAMA_FLASH_ATTENTION=1

REM Start Ollama in a new window
start "Ollama Server (GPU)" cmd /k "ollama serve"

REM Wait for Ollama to start
echo.
echo [*] Waiting for Ollama to initialize (5 seconds)...
timeout /t 5 /nobreak

echo.
echo [2] Starting MindDoc AI Backend...
echo     Port: 8080
echo     API Docs: http://127.0.0.1:8080/docs
echo.

REM Start backend in current window
cd /d "%~dp0"
C:\Users\Shubh\anaconda3\python.exe run_server.py

pause
