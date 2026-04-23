#!/usr/bin/env powershell
# MindDoc AI - GPU-Accelerated Startup with PowerShell
# Launches Ollama + Backend + Frontend (optional)

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "   MindDoc AI - GPU-Accelerated Startup" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

# Set Ollama environment variables for GPU optimization
$env:OLLAMA_MODEL = "gpt-oss:120b-cloud"
$env:OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_SCHED_SPREAD = "1"
$env:OLLAMA_DEBUG = "0"
$env:OLLAMA_FLASH_ATTENTION = "1"

Write-Host "[1] Starting Ollama server on GPU..." -ForegroundColor Yellow
Write-Host "    Model: gpt-oss:120b-cloud" -ForegroundColor Gray
Write-Host "    GPU: NVIDIA RTX 3050" -ForegroundColor Gray
Write-Host "    Keep this window open while using MindDoc AI`n" -ForegroundColor Gray

# Start Ollama in background job
$ollamaJob = Start-Job -ScriptBlock {
    $env:OLLAMA_MODEL = "gpt-oss:120b-cloud"
    $env:OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
    $env:OLLAMA_MAX_LOADED_MODELS = "1"
    $env:OLLAMA_SCHED_SPREAD = "1"
    $env:OLLAMA_FLASH_ATTENTION = "1"
    ollama serve
}

# Wait for Ollama to initialize
Write-Host "[*] Waiting for Ollama to initialize (5 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Verify Ollama is running
$ollamaReady = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
        $ollamaReady = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ollamaReady) {
    Write-Host "[OK] Ollama is running on GPU`n" -ForegroundColor Green
} else {
    Write-Host "[!] Warning: Ollama might not be responding yet`n" -ForegroundColor Yellow
}

Write-Host "[2] Starting MindDoc AI Backend..." -ForegroundColor Yellow
Write-Host "    Port: 8080" -ForegroundColor Gray
Write-Host "    API Docs: http://127.0.0.1:8080/docs`n" -ForegroundColor Gray

# Start backend
cd $PSScriptRoot
& C:\Users\Shubh\anaconda3\python.exe run_server.py

# Cleanup
Stop-Job -Job $ollamaJob
Remove-Job -Job $ollamaJob
