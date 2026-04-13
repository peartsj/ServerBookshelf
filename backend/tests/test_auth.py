from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_register_and_me_with_bearer_token() -> None:
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={"username": "Alice", "password": "secret123", "password_confirmation": "secret123"},
    )
    assert register_response.status_code == 201

    token = register_response.json()["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "alice"


def test_register_rejects_duplicate_username() -> None:
    client = TestClient(app)

    first = client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret123", "password_confirmation": "secret123"},
    )
    assert first.status_code == 201

    second = client.post(
        "/auth/register",
        json={"username": "alice", "password": "other123", "password_confirmation": "other123"},
    )
    assert second.status_code == 409


def test_register_rejects_password_confirmation_mismatch() -> None:
    client = TestClient(app)

    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret123", "password_confirmation": "different"},
    )
    assert response.status_code == 422


def test_login_and_me_with_bearer_token() -> None:
    client = TestClient(app)

    login_response = client.post("/auth/login", json={"username": "Alice", "password": "secret123"})
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "alice"


def test_bearer_token_precedence_over_query_username() -> None:
    client = TestClient(app)

    login_response = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    token = login_response.json()["access_token"]

    payload = {
        "title": "Token Scoped",
        "author_name": "Token Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/alice/ebooks/token-scoped.pdf",
            }
        ],
    }

    create_response = client.post(
        "/ebooks?username=bob",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    assert create_response.json()["owner_username"] == "alice"


def test_invalid_bearer_token_rejected() -> None:
    client = TestClient(app)

    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert response.status_code == 401


def test_bearer_token_precedence_on_patch_mutation() -> None:
    client = TestClient(app)

    token = client.post("/auth/login", json={"username": "alice", "password": "secret123"}).json()["access_token"]

    payload = {
        "title": "Token Patch",
        "author_name": "Token Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/alice/ebooks/token-patch.pdf",
            }
        ],
    }
    create = client.post("/ebooks", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert create.status_code == 201
    ebook_id = create.json()["id"]

    patch = client.patch(
        f"/ebooks/{ebook_id}?username=bob",
        json={"title": "Token Patch Updated"},
        headers={"Authorization": f"Bearer {token}", "X-Bookshelf-User": "charlie"},
    )
    assert patch.status_code == 200
    assert patch.json()["title"] == "Token Patch Updated"
    assert patch.json()["owner_username"] == "alice"


def test_bearer_token_precedence_on_delete_mutation() -> None:
    client = TestClient(app)

    token = client.post("/auth/login", json={"username": "alice", "password": "secret123"}).json()["access_token"]

    payload = {
        "title": "Token Delete",
        "author_name": "Token Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/alice/ebooks/token-delete.pdf",
            }
        ],
    }
    create = client.post("/ebooks", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert create.status_code == 201
    ebook_id = create.json()["id"]

    delete = client.delete(
        f"/ebooks/{ebook_id}?username=bob",
        headers={"Authorization": f"Bearer {token}", "X-Bookshelf-User": "charlie"},
    )
    assert delete.status_code == 204

    fetch = client.get(f"/ebooks/{ebook_id}", headers={"Authorization": f"Bearer {token}"})
    assert fetch.status_code == 404


def test_login_rejects_wrong_password_for_existing_user() -> None:
    client = TestClient(app)

    first = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    assert first.status_code == 200

    second = client.post("/auth/login", json={"username": "alice", "password": "wrong-password"})
    assert second.status_code == 401


def test_protected_endpoint_requires_token() -> None:
    client = TestClient(app)

    response = client.get("/ebooks")
    assert response.status_code == 401
