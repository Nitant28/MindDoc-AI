import os
import subprocess
import shutil
from typing import Optional

GGUF_SEARCH_DIRS = [
    os.path.join(os.getcwd(), 'models'),
]

SERVER_CANDIDATES = [
    os.path.join(os.getcwd(), 'llama.cpp', 'server'),
    os.path.join(os.getcwd(), 'llama.cpp', 'main'),
    os.path.join(os.getcwd(), 'server'),
    os.path.join(os.getcwd(), 'server.exe'),
]


def find_gguf_file() -> Optional[str]:
    for base in GGUF_SEARCH_DIRS:
        for root, _, files in os.walk(base):
            for f in files:
                if f.lower().endswith('.gguf'):
                    return os.path.join(root, f)
    return None


def find_server_binary() -> Optional[str]:
    # check candidates first
    for p in SERVER_CANDIDATES:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    # search PATH
    binname = shutil.which('server') or shutil.which('server.exe')
    if binname:
        return binname
    return None


class LlamaServerProcess:
    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.gguf_path: Optional[str] = None

    def start(self, port: int = 8080, ctx_size: int = 4096, threads: int = 8) -> bool:
        if self.proc and self.proc.poll() is None:
            return True
        gguf = find_gguf_file()
        if not gguf:
            return False
        server = find_server_binary()
        if not server:
            return False

        cmd = [server, '-m', gguf, '--port', str(port), '--ctx-size', str(ctx_size), '--threads', str(threads)]
        try:
            # start detached
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.environ['LLAMA_URL'] = f'http://127.0.0.1:{port}/v1/chat/completions'
            self.gguf_path = gguf
            return True
        except Exception:
            return False

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass


_MANAGER = LlamaServerProcess()


def start_if_possible():
    try:
        return _MANAGER.start()
    except Exception:
        return False


def stop_if_running():
    try:
        _MANAGER.stop()
    except Exception:
        pass
