"""
kaggle_downloader.py
Downloads relevant tax/legal datasets from Kaggle using the Kaggle API.
"""

import os
import subprocess

# Ensure Kaggle API credentials are set up in ~/.kaggle/kaggle.json
# User must place their kaggle.json in the correct location before running

# List of Kaggle dataset slugs to download (can be expanded)
DATASETS = [
    "shivam2503/indian-income-tax-dataset",
    "ruchi798/tax-dataset",
    "ruchi798/finance-complaints",
    "ruchi798/indian-legal-case-data",
    "ruchi798/indian-court-cases",
    "ruchi798/indian-taxation-dataset"
]

os.makedirs("kaggle_datasets", exist_ok=True)

for ds in DATASETS:
    print(f"Downloading {ds} ...")
    subprocess.run([
        "kaggle", "datasets", "download", "-d", ds, "-p", "kaggle_datasets", "--unzip"
    ], check=False)

print("Kaggle datasets download complete.")
