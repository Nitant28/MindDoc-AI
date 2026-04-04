import requests
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"  # Change to your live URL
API_KEY = os.getenv("API_KEY", "hackathon2024")  # Use your actual API key

def test_health():
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200 and response.json() == {"status": "ok"}:
            print("✅ /health: PASS")
            return True
        else:
            print(f"❌ /health: FAIL - Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ /health: ERROR - {e}")
        return False

def test_analyze_document_no_auth():
    print("Testing /analyze-document with no auth...")
    try:
        # Create a dummy file
        files = {'file': ('test.pdf', b'dummy content', 'application/pdf')}
        response = requests.post(f"{BASE_URL}/analyze-document", files=files)
        if response.status_code == 401 and "Missing API key" in response.json().get("message", ""):
            print("✅ No auth: PASS")
            return True
        else:
            print(f"❌ No auth: FAIL - Status: {response.status_code}, Response: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ No auth: ERROR - {e}")
        return False

def test_analyze_document_invalid_auth():
    print("Testing /analyze-document with invalid auth...")
    try:
        headers = {"Authorization": "Bearer invalid_key"}
        files = {'file': ('test.pdf', b'dummy content', 'application/pdf')}
        response = requests.post(f"{BASE_URL}/analyze-document", headers=headers, files=files)
        if response.status_code == 403 and "Invalid API key" in response.json().get("message", ""):
            print("✅ Invalid auth: PASS")
            return True
        else:
            print(f"❌ Invalid auth: FAIL - Status: {response.status_code}, Response: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Invalid auth: ERROR - {e}")
        return False

def test_analyze_document_invalid_file():
    print("Testing /analyze-document with invalid file type...")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        files = {'file': ('test.txt', b'dummy content', 'text/plain')}
        response = requests.post(f"{BASE_URL}/analyze-document", headers=headers, files=files)
        if response.status_code == 400 and "Unsupported file type" in response.json().get("message", ""):
            print("✅ Invalid file: PASS")
            return True
        else:
            print(f"❌ Invalid file: FAIL - Status: {response.status_code}, Response: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Invalid file: ERROR - {e}")
        return False

def test_analyze_document_valid():
    print("Testing /analyze-document with valid file...")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        # Create a simple PDF-like content (this will fail extraction but test the pipeline)
        files = {'file': ('test.pdf', b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF', 'application/pdf')}
        response = requests.post(f"{BASE_URL}/analyze-document", headers=headers, files=files, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] == "success":
                print("✅ Valid file: PASS")
                print(f"   Summary: {data.get('summary', '')[:100]}...")
                print(f"   Confidence: {data.get('confidence_score', 0)}")
                return True
            else:
                print(f"❌ Valid file: FAIL - Invalid response format: {data}")
                return False
        else:
            print(f"❌ Valid file: FAIL - Status: {response.status_code}, Response: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Valid file: TIMEOUT - Response took too long (>30s)")
        return False
    except Exception as e:
        print(f"❌ Valid file: ERROR - {e}")
        return False

def run_all_tests():
    print("=" * 50)
    print("API TESTING SUITE")
    print("=" * 50)
    
    tests = [
        test_health,
        test_analyze_document_no_auth,
        test_analyze_document_invalid_auth,
        test_analyze_document_invalid_file,
        test_analyze_document_valid
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ Some tests failed. Check logs above.")
    print("=" * 50)

if __name__ == "__main__":
    run_all_tests()