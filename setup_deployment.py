#!/usr/bin/env python3
"""
Quick deployment setup script for MindDoc AI
Prepares your project for deployment to Render, Railway, or Vercel
"""

import os
import subprocess
import sys
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_git():
    """Check if Git is initialized"""
    if not Path(".git").exists():
        print("❌ Git not initialized")
        print("\nInitializing Git repository...")
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Initial MindDoc AI commit"], check=True)
        print("✅ Git initialized and committed")
        return True
    else:
        print("✅ Git repository found")
        return False

def check_files():
    """Check if deployment files exist"""
    files_to_check = [
        "Dockerfile",
        "Procfile",
        "render.yaml",
        "railway.json",
        ".gitignore",
        ".env.example",
        "frontend/.env.production"
    ]
    
    missing = []
    for file in files_to_check:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print(f"❌ Missing deployment files: {', '.join(missing)}")
        return False
    else:
        print("✅ All deployment files present")
        return True

def check_env():
    """Check if .env file exists"""
    if Path(".env").exists():
        print("✅ .env file found")
        return True
    else:
        print("⚠️  .env file not found")
        print("   Create .env file with configuration from .env.example")
        print("   Required: OPENAI_API_KEY, JWT_SECRET")
        return False

def generate_secret():
    """Generate a secure JWT secret"""
    try:
        import secrets
        return secrets.token_hex(32)
    except:
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def main():
    os.chdir(Path(__file__).parent)
    
    print_header("MindDoc AI - Deployment Setup")
    
    print("Checking deployment prerequisites...\n")
    
    # Check Git
    print("[1/3] Checking Git...")
    git_ok = check_git()
    
    # Check files
    print("\n[2/3] Checking deployment files...")
    files_ok = check_files()
    
    # Check .env
    print("\n[3/3] Checking environment configuration...")
    env_ok = check_env()
    
    # Summary
    print_header("Deployment Readiness Summary")
    
    status = "✅ READY" if (files_ok and env_ok) else "⚠️  NEEDS SETUP"
    print(f"Status: {status}\n")
    
    if not env_ok:
        print("ACTION REQUIRED:")
        print("1. Copy .env.example to .env")
        print("2. Fill in OPENAI_API_KEY from https://platform.openai.com/api-keys")
        print("3. Generate JWT_SECRET:")
        print(f"   {generate_secret()}")
        print()
    
    print("NEXT STEPS:")
    print("\n1️⃣  For RENDER (Easiest):")
    print("   - Push to GitHub")
    print("   - Go to https://render.com")
    print("   - Connect GitHub repo")
    print("   - Set OPENAI_API_KEY env var")
    print("   - Deploy!")
    
    print("\n2️⃣  For RAILWAY:")
    print("   - Push to GitHub")
    print("   - Go to https://railway.app")
    print("   - Import from GitHub")
    print("   - Set environment variables")
    print("   - Deploy!")
    
    print("\n3️⃣  For VERCEL + RENDER (Best):")
    print("   - Deploy frontend to Vercel")
    print("   - Deploy backend to Render")
    print("   - Set API URL in frontend .env")
    
    print("\n📖 Read DEPLOYMENT_GUIDE.md for detailed instructions")
    print_header("Good luck! 🚀")

if __name__ == "__main__":
    main()
