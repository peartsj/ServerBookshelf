import pytest
from fastapi.testclient import TestClient

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


def _auth_headers(client: TestClient, username: str = "default", password: str = "testpass") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_ebook_for_user(client: TestClient, username: str = "default") -> int:
    headers = _auth_headers(client, username=username)
    payload = {
        "title": "Category Test Book",
        "author_name": "Category Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": f"uploads/ebooks/{username}-category-test.pdf",
            }
        ],
    }
    response = client.post("/ebooks", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_get_categories_returns_empty_list(client: TestClient) -> None:
    response = client.get("/categories", headers=_auth_headers(client))

    assert response.status_code == 200
    assert response.json() == []


def test_post_categories_creates_and_reuses_category(client: TestClient) -> None:
    headers = _auth_headers(client)
    first = client.post("/categories", json={"name": "Fantasy"}, headers=headers)
    second = client.post("/categories", json={"name": "Fantasy"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["name"] == "Fantasy"
    assert first.json()["id"] == second.json()["id"]


def test_attach_category_to_ebook_and_list_for_owner(client: TestClient) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")
    category = client.post("/categories", json={"name": "Sci-Fi"}, headers=alice_headers).json()
    ebook_id = _create_ebook_for_user(client, username="alice")

    attach_response = client.post(f"/ebooks/{ebook_id}/categories/{category['id']}", headers=alice_headers)

    assert attach_response.status_code == 204

    list_owner = client.get("/categories", headers=alice_headers)
    list_other_user = client.get("/categories", headers=bob_headers)

    assert list_owner.status_code == 200
    assert list_owner.json() == [{"id": category["id"], "name": "Sci-Fi"}]
    assert list_other_user.status_code == 200
    assert list_other_user.json() == []


def test_attach_category_respects_user_scope(client: TestClient) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")
    category = client.post("/categories", json={"name": "Architecture"}, headers=alice_headers).json()
    ebook_id = _create_ebook_for_user(client, username="alice")

    response = client.post(f"/ebooks/{ebook_id}/categories/{category['id']}", headers=bob_headers)

    assert response.status_code == 404


def test_detach_category_from_ebook(client: TestClient) -> None:
    headers = _auth_headers(client)
    category = client.post("/categories", json={"name": "DevOps"}, headers=headers).json()
    ebook_id = _create_ebook_for_user(client)

    attach = client.post(f"/ebooks/{ebook_id}/categories/{category['id']}", headers=headers)
    assert attach.status_code == 204

    detach = client.delete(f"/ebooks/{ebook_id}/categories/{category['id']}", headers=headers)
    assert detach.status_code == 204

    categories = client.get("/categories", headers=headers)
    assert categories.status_code == 200
    assert categories.json() == []
