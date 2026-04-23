"""
model_update_manager.py
Auto-update manager for GGUF models and llama.cpp server binary.
"""
import os
import requests
import shutil
class ModelUpdateManager:
    def __init__(self, model_dir="models", server_dir="llama_bin"):
        self.model_dir = model_dir
        self.server_dir = server_dir
    def check_model_update(self, repo_url, filename, dest):
        # Placeholder: Check remote version, download if newer
        url = f"{repo_url}/{filename}"
        local_path = os.path.join(dest, filename)
        try:
            r = requests.head(url, timeout=5)
            remote_size = int(r.headers.get('content-length', 0))
            if not os.path.exists(local_path) or os.path.getsize(local_path) != remote_size:
                self.download_file(url, local_path)
                return True
        except Exception:
            pass
        return False
    def download_file(self, url, dest):
        with requests.get(url, stream=True) as r:
            with open(dest, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
    def check_server_update(self, release_url, asset_name, dest):
        # Placeholder: Download latest server binary if missing or outdated
        url = f"{release_url}/{asset_name}"
        local_path = os.path.join(dest, asset_name)
        try:
            r = requests.head(url, timeout=5)
            remote_size = int(r.headers.get('content-length', 0))
            if not os.path.exists(local_path) or os.path.getsize(local_path) != remote_size:
                self.download_file(url, local_path)
                return True
        except Exception:
            pass
        return False
model_update_manager = ModelUpdateManager()
# Example usage:
# model_update_manager.check_model_update('https://huggingface.co/Qwen/Qwen-2-7B-Instruct/resolve/main', 'qwen2-7b-instruct-q2_k.gguf', 'models/qwen2-7b')
# model_update_manager.check_server_update('https://github.com/ggerganov/llama.cpp/releases/latest/download', 'server.exe', 'llama_bin')
