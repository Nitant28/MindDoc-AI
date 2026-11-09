import os
import sys
import tempfile
from pathlib import Path

# Isolated DB + deterministic offline mode (no LLM calls) — must be set before importing the app.
_tmp = tempfile.mkdtemp(prefix="minddoc-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["STORAGE_DIR"] = str(Path(_tmp) / "uploads")
os.environ["LLM_PROVIDER_ORDER"] = "none"
os.environ["MINDDOC_SKIP_WARMUP"] = "1"
os.environ["ENABLE_VISION_CAPTIONS"] = "false"
os.environ["ENABLE_RERANKER"] = os.environ.get("TEST_RERANKER", "false")
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 32
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def _auth(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def alice(client):
    return _auth(client, "alice@example.com")


@pytest.fixture(scope="session")
def bob(client):
    return _auth(client, "bob@example.com")
