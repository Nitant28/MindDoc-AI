"""Download a GGUF model file from Hugging Face to a destination folder.

Usage:
  python scripts/download_qwen2_gguf.py --repo <repo-id> --filename qwen2-7b-instruct-q4_k_m.gguf --dest models/qwen2-7b

Note: Some GGUF models are large (many GB). You may need a HF token for private/ gated models.
"""
import argparse
import os
import sys
from huggingface_hub import snapshot_download


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True, help='Hugging Face repo id (e.g., Qwen/Qwen-2-7B-Instruct)')
    p.add_argument('--filename', required=True, help='GGUF filename to download')
    p.add_argument('--dest', required=True, help='Destination folder')
    p.add_argument('--revision', default=None)
    args = p.parse_args()

    os.makedirs(args.dest, exist_ok=True)
    print(f'Downloading {args.filename} from {args.repo} into {args.dest} (this can be large)')
    try:
        path = snapshot_download(
            repo_id=args.repo,
            revision=args.revision,
            cache_dir=args.dest,
            repo_type='model',
            allow_patterns=[f"**/{args.filename}"]
        )
        print('Downloaded to', path)
    except Exception as e:
        print('Failed to download:', e)
        sys.exit(2)


if __name__ == '__main__':
    main()
