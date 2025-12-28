This folder contains helper scripts to fetch or place a prebuilt llama.cpp "server" binary.

PowerShell (Windows):

  - Run with an explicit URL:

    powershell -ExecutionPolicy Bypass -File .\scripts\download_llama_server.ps1 -DownloadUrl "https://example.com/server.exe"

  - Or set environment variable and run:

    $env:LLAMA_SERVER_DOWNLOAD_URL = 'https://example.com/server.exe'
    powershell -ExecutionPolicy Bypass -File .\scripts\download_llama_server.ps1

Shell (Linux/macOS):

  - Run with env var:

    LLAMA_SERVER_DOWNLOAD_URL=https://example.com/server ./scripts/download_llama_server.sh

If automatic download is not possible in your environment, manually place a prebuilt server binary at:

  ./llama_bin/server.exe  (Windows)
  ./llama_bin/server      (Linux/macOS)

After the server binary is present, ensure you also have a GGUF model file under `models/` (for example `models/qwen2-7b-instruct-q2_k.gguf`).

Then start the backend (the app's lifecycle will try to detect and start the server):

  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

If the manager cannot auto-start the server, run the server manually pointing at your GGUF file and set `LLAMA_URL` accordingly, e.g.:

  (Start the server manually; commands depend on the distribution you downloaded.)
  set LLAMA_URL=http://127.0.0.1:8080/v1/chat/completions
