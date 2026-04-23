# MindDoc AI - GPU Startup Guide

## Quick Start (One Click)

### Option 1: Batch File (Recommended - Windows)
Double-click: **`start_with_gpu.bat`**

This will automatically:
- ✅ Start Ollama server on your GPU
- ✅ Start MindDoc AI backend
- ✅ Keep both running for you

---

### Option 2: PowerShell Script
```powershell
# Right-click PowerShell and select "Run as Administrator"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.\start_with_gpu.ps1
```

---

### Option 3: Manual Steps (For debugging)

#### Step 1: Start Ollama on GPU
```powershell
$env:OLLAMA_MODEL="gpt-oss:120b-cloud"
$env:OLLAMA_MAX_LOADED_MODELS="1"
$env:OLLAMA_FLASH_ATTENTION="1"
ollama serve
```
Expected output:
```
Listening on 127.0.0.1:11434
```

#### Step 2: Start Backend (New Terminal)
```powershell
C:\Users\Shubh\anaconda3\python.exe run_server.py
```
Expected output:
```
Uvicorn running on http://127.0.0.1:8080
Application startup complete
```

#### Step 3: Start Frontend (New Terminal)
```powershell
cd frontend
npm run dev
```
Expected output:
```
Local: http://localhost:5173
```

---

## What's Running After Startup

| Service | URL | Status |
|---------|-----|--------|
| **Ollama API** | http://127.0.0.1:11434 | ✅ GPU-accelerated |
| **Backend API** | http://127.0.0.1:8080 | ✅ Running |
| **Frontend** | http://127.0.0.1:5173 | ✅ Dev Server |
| **API Docs** | http://127.0.0.1:8080/docs | 📖 Docs |

---

## Monitor GPU Usage

Open a new PowerShell and run:
```powershell
# Watch GPU in real-time
nvidia-smi -l 1

# Or check once
nvidia-smi
```

You should see:
- `gpt-oss:120b-cloud` (or your configured Ollama model) loaded on GPU
- GPU Utilization increasing during queries
- RTX 3050 vRAM: ~5-6 GB in use

---

## Performance Tips

### For Faster Response Times
1. **Close unnecessary apps** to free GPU memory
   - Close Chrome/Edge (uses 1-2 GB)
   - Close VS Code (uses 500 MB - 2 GB)
   - Close other GPU-heavy applications

2. **Keep Ollama running** between queries (models stay in GPU memory)

3. **One model at a time** 
   - `deepseek-r1:8b` is optimal for your RTX 3050

---

## Environment Variables (Already Set)

The startup scripts automatically configure:

| Variable | Value | Purpose |
|----------|-------|---------|
| `OLLAMA_MODEL` | `gpt-oss:120b-cloud` | Sets default model |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Only 1 model in memory |
| `OLLAMA_SCHED_SPREAD` | `1` | Distribute across all GPUs |
| `OLLAMA_FLASH_ATTENTION` | `1` | Enable fast attention (faster) |

---

## Troubleshooting

### Ollama not starting
```powershell
# Check if Ollama is already running
ollama ps

# Force kill old processes
Stop-Process -Name ollama -Force

# Try again
ollama serve
```

### GPU not being used
```powershell
# Verify CUDA is working
nvidia-smi

# Check Ollama debug info
$env:OLLAMA_DEBUG="1"
ollama serve
```

### Backend won't start
```powershell
# Check if port 8080 is in use
netstat -ano | findstr :8080

# Kill the process if it exists
Stop-Process -Id <PID> -Force
```

### Model too slow
1. Ensure Ollama is actually running: `http://127.0.0.1:11434/api/tags`
2. Check GPU usage: `nvidia-smi`
3. Close other apps using GPU
4. Verify model is loaded in GPU memory

---

## What's Configured

✅ **Model**: gpt-oss:120b-cloud (or your configured Ollama model)
✅ **GPU**: NVIDIA RTX 3050 (6 GB vRAM)
✅ **Backend**: FastAPI + SQLite
✅ **Frontend**: React + Vite + Tailwind
✅ **RAG**: FAISS + LangChain
✅ **Database**: SQLite (./minddoc.db)

---

## Next Steps

1. **Run the startup script** → `start_with_gpu.bat`
2. **Open browser** → http://localhost:5173
3. **Login** (or create account)
4. **Upload documents** (PDF, DOCX, images)
5. **Ask questions** → Get AI-powered answers from your documents

---

## Need Help?

Check logs in each terminal window for errors. The three terminals (Ollama, Backend, Frontend) will show real-time logs.

**Enjoy MindDoc AI with GPU acceleration!** 🚀
