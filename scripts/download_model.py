"""Download a model from Hugging Face to a local folder (safe downloader).

Usage:
  python scripts/download_model.py --repo gpt2-medium --dest models/gpt2-medium
"""
import argparse
import os
import sys
import logging
from huggingface_hub import snapshot_download

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('download_model')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True, help='Hugging Face repo id (or local folder)')
    p.add_argument('--dest', required=True, help='Destination folder')
    p.add_argument('--revision', default=None)
    args = p.parse_args()

    os.makedirs(args.dest, exist_ok=True)
    logger.info('Downloading %s to %s', args.repo, args.dest)
    try:
        path = snapshot_download(repo_id=args.repo, revision=args.revision, cache_dir=args.dest, repo_type='model')
        logger.info('Downloaded snapshot to %s', path)
    except Exception as e:
        logger.exception('Failed to download: %s', e)
        sys.exit(2)


if __name__ == '__main__':
    main()
