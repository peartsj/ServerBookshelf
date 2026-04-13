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
    settings.max_upload_size_mb = 5

    try:
        yield tmp_path
    finally:
        settings.upload_root = old_root
        settings.max_upload_size_mb = old_max_size


def _auth_headers(client: TestClient, username: str, password: str = "testpass") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_staged_upload_create_category_flow(client: TestClient, upload_settings: Path) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")

    upload_response = client.post(
        "/uploads/ebook-file",
        headers=alice_headers,
        files={"file": ("flow-book.epub", b"PK\x03\x04staged-epub", "application/epub+zip")},
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    assert upload_payload["storage_path"].startswith("uploads/alice/ebooks/")

    create_payload = {
        "title": "Flow-Driven Book",
        "author_name": "Flow Author",
        "description": "Created via staged upload flow",
        "files": [
            {
                "media_type": "ebook",
                "file_format": upload_payload["file_format"],
                "storage_path": upload_payload["storage_path"],
                "file_size_bytes": upload_payload["size_bytes"],
                "checksum_sha256": upload_payload["checksum_sha256"],
            }
        ],
    }
    create_response = client.post("/ebooks", json=create_payload, headers=alice_headers)
    assert create_response.status_code == 201
    ebook_id = create_response.json()["id"]

    category_response = client.post("/categories", json={"name": "Workflows"}, headers=alice_headers)
    assert category_response.status_code in (200, 201)
    category_id = category_response.json()["id"]

    attach_response = client.post(f"/ebooks/{ebook_id}/categories/{category_id}", headers=alice_headers)
    assert attach_response.status_code == 204

    list_response = client.get("/ebooks", headers=alice_headers)
    assert list_response.status_code == 200
    ebooks = list_response.json()["items"]
    assert len(ebooks) == 1
    assert ebooks[0]["title"] == "Flow-Driven Book"
    assert "Workflows" in ebooks[0]["genre_names"]
    assert ebooks[0]["files"][0]["checksum_sha256"] == upload_payload["checksum_sha256"]

    categories_response = client.get("/categories", headers=alice_headers)
    assert categories_response.status_code == 200
    assert categories_response.json() == [{"id": category_id, "name": "Workflows"}]

    detach_response = client.delete(f"/ebooks/{ebook_id}/categories/{category_id}", headers=alice_headers)
    assert detach_response.status_code == 204

    categories_after_detach = client.get("/categories", headers=alice_headers)
    assert categories_after_detach.status_code == 200
    assert categories_after_detach.json() == []

    other_user = client.get("/ebooks", headers=bob_headers)
    assert other_user.status_code == 200
    assert other_user.json()["items"] == []
