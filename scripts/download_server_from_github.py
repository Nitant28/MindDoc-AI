#!/usr/bin/env python3
"""Download a prebuilt llama.cpp server binary from GitHub releases and start it.

Tries repositories in order: ggml-org/llama.cpp, ggerganov/llama.cpp
Finds an asset with 'server' or 'windows' in the name. If a .zip is found it will
extract and look for an executable named 'server' or 'server.exe'. The final binary
is placed in ./llama_bin/server(.exe) and made executable.
"""
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import urllib.error
from zipfile import ZipFile

REPOS = ["ggml-org/llama.cpp", "ggerganov/llama.cpp"]
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'llama_bin')
os.makedirs(OUT_DIR, exist_ok=True)

def fetch_latest_release(repo):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.load(r)
    except Exception:
        return None

def download_url(url, dest_path):
    print('Downloading', url)
    with urllib.request.urlopen(url, timeout=60) as r, open(dest_path, 'wb') as out:
        shutil.copyfileobj(r, out)

def try_extract_zip(zippath, out_dir):
    try:
        with ZipFile(zippath) as z:
            for name in z.namelist():
                low = name.lower()
                if low.endswith('server') or low.endswith('server.exe') or ('server' in os.path.basename(low)):
                    z.extract(name, out_dir)
                    return os.path.join(out_dir, name)
    except Exception:
        return None
    return None

def pick_asset(assets):
    # prefer direct server executables
    for a in assets:
        name = a.get('name','').lower()
        if 'server' in name and (name.endswith('.exe') or name.endswith('.zip') or name.endswith('.tar.gz') or name.endswith('.gz')):
            return a
    # fallback: windows zips
    for a in assets:
        name = a.get('name','').lower()
        if 'windows' in name and (name.endswith('.zip') or name.endswith('.exe')):
            return a
    return None

def main():
    print('Looking for prebuilt llama.cpp server releases...')
    for repo in REPOS:
        rel = fetch_latest_release(repo)
        if not rel:
            continue
        assets = rel.get('assets', [])
        if not assets:
            continue
        asset = pick_asset(assets)
        if not asset:
            continue
        url = asset.get('browser_download_url')
        if not url:
            continue

        tmpdir = tempfile.mkdtemp(prefix='llama_dl_')
        try:
            name = asset.get('name', 'server_asset')
            dest = os.path.join(tmpdir, name)
            download_url(url, dest)
            # if zip, try extract
            if dest.lower().endswith('.zip'):
                extracted = try_extract_zip(dest, tmpdir)
                if extracted:
                    final_name = os.path.basename(extracted)
                    final_path = os.path.join(OUT_DIR, final_name)
                    shutil.move(extracted, final_path)
                    os.chmod(final_path, 0o755)
                    print('Placed server at', final_path)
                    return final_path
            elif dest.lower().endswith('.exe') or dest.lower().endswith('server'):
                final_path = os.path.join(OUT_DIR, os.path.basename(dest))
                shutil.move(dest, final_path)
                os.chmod(final_path, 0o755)
                print('Placed server at', final_path)
                return final_path
            else:
                # try heuristics: search extracted tmp dir for executable
                for root, _, files in os.walk(tmpdir):
                    for f in files:
                        if f.lower() in ('server', 'server.exe') or 'server' in f.lower():
                            src = os.path.join(root, f)
                            final = os.path.join(OUT_DIR, f)
                            shutil.move(src, final)
                            os.chmod(final, 0o755)
                            print('Placed server at', final)
                            return final
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    print('No suitable prebuilt server asset found in releases.')
    print('You can manually place a server binary at', OUT_DIR)
    return None

if __name__ == '__main__':
    path = main()
    if not path:
        sys.exit(2)
    # attempt to start via llama_manager
    # set PYTHONPATH so imports work when running directly from scripts
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    try:
        from app.services.llama_manager import start_if_possible
        started = start_if_possible()
        print('start_if_possible ->', started)
        if not started:
            print('Manager did not start the server. You can start the server manually:')
            print(path)
    except Exception as e:
        print('Could not import llama_manager or start manager:', e)
        sys.exit(3)
