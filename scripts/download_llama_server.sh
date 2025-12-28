#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="$SCRIPT_DIR/../llama_bin"
mkdir -p "$DEST_DIR"
OUT_PATH="$DEST_DIR/server"

if [ ! -z "${LLAMA_SERVER_DOWNLOAD_URL:-}" ]; then
  echo "Attempting download from: $LLAMA_SERVER_DOWNLOAD_URL"
  curl -L "$LLAMA_SERVER_DOWNLOAD_URL" -o "$OUT_PATH" || {
    echo "Download failed"
    exit 1
  }
  chmod +x "$OUT_PATH"
  echo "Downloaded server to: $OUT_PATH"
  exit 0
fi

echo "No LLAMA_SERVER_DOWNLOAD_URL set."
echo "Options:"
echo "  1) Export LLAMA_SERVER_DOWNLOAD_URL and run this script. Example:" \
     "LLAMA_SERVER_DOWNLOAD_URL=https://example.com/server.exe ./download_llama_server.sh"
echo "  2) Manually place a prebuilt server binary at: $OUT_PATH"
echo "  3) Build from source: git clone https://github.com/ggerganov/llama.cpp && follow build instructions"
exit 1
