import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def upload_settings(tmp_path: Path):
    old_root = settings.upload_root
    old_max_size = settings.max_upload_size_mb

    settings.upload_root = str(tmp_path / "uploads")
    settings.max_upload_size_mb = 1

    try:
        yield tmp_path
    finally:
        settings.upload_root = old_root
        settings.max_upload_size_mb = old_max_size


def _auth_headers(client: TestClient, username: str = "alice", password: str = "testpass") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_upload_ebook_file_success(client: TestClient, upload_settings: Path) -> None:
    content = b"PK\x03\x04epub-content"
    headers = _auth_headers(client, username="alice")

    response = client.post(
        "/uploads/ebook-file",
        headers=headers,
        files={"file": ("my-book.epub", content, "application/epub+zip")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["owner_username"] == "alice"
    assert body["file_format"] == "epub"
    assert body["storage_path"].startswith("uploads/alice/ebooks/")
    assert body["size_bytes"] == len(content)
    assert body["checksum_sha256"] == hashlib.sha256(content).hexdigest()

    stored_path = Path(settings.upload_root) / "alice" / "ebooks" / body["stored_filename"]
    assert stored_path.exists()


def test_upload_ebook_file_epub_success(client: TestClient, upload_settings: Path) -> None:
    content = b"PK\x03\x04epub-content"
    headers = _auth_headers(client, username="alice")

    response = client.post(
        "/uploads/ebook-file",
        headers=headers,
        files={"file": ("my-book.epub", content, "application/epub+zip")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file_format"] == "epub"
    assert body["checksum_sha256"] == hashlib.sha256(content).hexdigest()


def test_upload_ebook_file_rejects_unsupported_extension(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client)
    response = client.post(
        "/uploads/ebook-file",
        headers=headers,
        files={"file": ("script.exe", b"MZ-not-ebook", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_upload_ebook_file_rejects_oversized_payload(client: TestClient, upload_settings: Path) -> None:
    oversized = b"a" * (settings.max_upload_size_mb * 1024 * 1024 + 1)
    headers = _auth_headers(client)

    response = client.post(
        "/uploads/ebook-file",
        headers=headers,
        files={"file": ("big-book.epub", oversized, "application/epub+zip")},
    )

    assert response.status_code == 413
    assert "File exceeds max size" in response.json()["detail"]


def test_upload_ebook_file_rejects_mismatched_content_type(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client)
    response = client.post(
        "/uploads/ebook-file",
        headers=headers,
        files={"file": ("my-book.epub", b"PK\x03\x04valid-epub", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported content type" in response.json()["detail"]


def test_upload_ebook_file_rejects_invalid_epub_signature(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client)
    response = client.post(
        "/uploads/ebook-file",
        headers=headers,
        files={"file": ("my-book.epub", b"NOT-AN-EPUB", "application/epub+zip")},
    )

    assert response.status_code == 400
    assert "not a valid EPUB" in response.json()["detail"]


def test_upload_ebook_file_rejects_empty_file(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client)
    response = client.post(
        "/uploads/ebook-file",
        headers=headers,
        files={"file": ("empty.epub", b"", "application/epub+zip")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
