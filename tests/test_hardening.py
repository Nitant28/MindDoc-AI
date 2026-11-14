"""Phase 0 hardening: upload caps, zip-bomb guard, per-user rate limits, OpenRouter provider wiring."""
import io
import zipfile

import pytest

from app.ai import llm
from app.core import security
from app.core.config import settings
from app.services import document_service


def _pdf(pages: int) -> bytes:
    from tests.pdfgen import make_pdf
    return make_pdf([[f"Page {i + 1} of a test document with enough text to parse."] for i in range(pages)])


def test_pdf_page_cap(monkeypatch):
    monkeypatch.setattr(settings, "max_pdf_pages", 2)
    with pytest.raises(ValueError, match="limit is 2"):
        document_service.parse_pdf(_pdf(3))
    assert len(document_service.parse_pdf(_pdf(2)).pages) == 2


def test_docx_zip_bomb_guard(monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", b"0" * (3 * 1024 * 1024))  # 3 MB of zeros compresses to a few KB
    monkeypatch.setattr(settings, "max_docx_uncompressed_mb", 1)
    with pytest.raises(ValueError, match="limit is 1 MB"):
        document_service.parse_docx(buf.getvalue())
    with pytest.raises(ValueError, match="Not a valid"):
        document_service.parse_docx(b"definitely not a zip")


def test_image_pixel_cap(monkeypatch):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(buf, format="PNG")
    monkeypatch.setattr(settings, "max_image_pixels", 100_000)
    with pytest.raises(ValueError, match="pixels"):
        document_service.parse_image(buf.getvalue())


def test_upload_rejects_oversized_pdf_with_400(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "max_pdf_pages", 1)
    r = client.post("/api/documents/upload", headers=alice,
                    files={"file": ("big.pdf", _pdf(2), "application/pdf")})
    assert r.status_code == 400 and "limit" in r.json()["detail"]


def test_auth_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(security.auth_limiter, "limit", 2)
    monkeypatch.setattr(security.auth_limiter, "hits", __import__("collections").defaultdict(__import__("collections").deque))
    bad = {"email": "nobody-limit@example.com", "password": "wrong-password-1"}
    codes = [client.post("/api/auth/login", json=bad).status_code for _ in range(3)]
    assert codes[:2] == [401, 401] and codes[2] == 429


def test_query_rate_limit_returns_429(client, monkeypatch):
    r = client.post("/api/auth/register", json={"email": "ratey@example.com", "password": "correct-horse-1"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    monkeypatch.setattr(security.query_limiter, "limit", 1)
    assert client.post("/api/chat/query", headers=h, json={"query": "hello?"}).status_code == 200
    assert client.post("/api/chat/query", headers=h, json={"query": "hello again?"}).status_code == 429


def test_openrouter_provider_is_openai_compatible(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    cfg = llm._provider_config("openrouter")
    assert cfg["kind"] == "openai" and cfg["url"].startswith("https://openrouter.ai/")
    url, headers, body = llm._build_request(cfg, "hi", "sys", None, 50, 0.1, False, None, stream=False)
    assert headers["Authorization"] == "Bearer test-key" and headers["X-Title"] == "MindDoc AI"
    assert body["messages"][0] == {"role": "system", "content": "sys"} and body["model"] == settings.openrouter_model
    assert "openrouter" in {p["name"] for p in llm.available_providers()}
