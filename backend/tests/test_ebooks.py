from pathlib import Path
import zipfile

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
    settings.upload_root = str(tmp_path / "uploads")
    try:
        yield tmp_path
    finally:
        settings.upload_root = old_root


def _auth_headers(client: TestClient, username: str = "default", password: str = "testpass") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _list_items(payload: dict) -> list[dict]:
    return payload["items"]


def _create_minimal_epub_with_cover(epub_path: Path, cover_bytes: bytes) -> None:
        epub_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(epub_path, "w") as archive:
                archive.writestr("mimetype", "application/epub+zip")
                archive.writestr(
                        "META-INF/container.xml",
                        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">
    <rootfiles>
        <rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/>
    </rootfiles>
</container>
""",
                )
                archive.writestr(
                        "OEBPS/content.opf",
                        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<package xmlns=\"http://www.idpf.org/2007/opf\" version=\"3.0\" unique-identifier=\"bookid\">
    <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">
        <dc:title>Cover Test</dc:title>
        <meta name=\"cover\" content=\"cover-image\"/>
    </metadata>
    <manifest>
        <item id=\"cover-image\" href=\"images/cover.png\" media-type=\"image/png\"/>
    </manifest>
    <spine/>
</package>
""",
                )
                archive.writestr("OEBPS/images/cover.png", cover_bytes)


def test_get_ebooks_returns_empty_list(client: TestClient) -> None:
    response = client.get("/ebooks", headers=_auth_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total_count"] == 0
    assert payload["total_pages"] == 0
    assert payload["page"] == 1


def test_post_ebook_creates_and_lists_record(client: TestClient) -> None:
    headers = _auth_headers(client)
    payload = {
        "title": "The Pragmatic Programmer",
        "author_name": "Andrew Hunt",
        "publisher_name": "Addison-Wesley",
        "genre_names": ["Software Engineering", "Programming"],
        "description": "A practical guide to software craftsmanship.",
        "publishing_year": 1999,
        "series_name": "Pragmatic Bookshelf Classics",
        "series_position": 1,
        "has_adaptation": True,
        "cover_art_path": "uploads/covers/pragmatic.jpg",
        "isbn_13": "9780201616224",
        "language_code": "en",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/ebooks/pragmatic-programmer.pdf",
                "file_size_bytes": 2048000,
            }
        ],
    }

    create_response = client.post("/ebooks", json=payload, headers=headers)

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["title"] == payload["title"]
    assert body["owner_username"] == "default"
    assert body["author_name"] == payload["author_name"]
    assert body["has_adaptation"] is True
    assert len(body["files"]) == 1
    assert body["files"][0]["file_format"] == "pdf"

    list_response = client.get("/ebooks", headers=headers)

    assert list_response.status_code == 200
    all_ebooks = _list_items(list_response.json())
    assert len(all_ebooks) == 1
    assert all_ebooks[0]["title"] == payload["title"]


def test_post_ebook_defaults_has_adaptation_to_false(client: TestClient) -> None:
    headers = _auth_headers(client)
    payload = {
        "title": "Clean Architecture",
        "author_name": "Robert C. Martin",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "epub",
                "storage_path": "uploads/ebooks/clean-architecture.epub",
            }
        ],
    }

    response = client.post("/ebooks", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.json()["has_adaptation"] is False


def test_get_ebook_by_id_returns_single_record(client: TestClient) -> None:
    headers = _auth_headers(client)
    create_payload = {
        "title": "Domain-Driven Design",
        "author_name": "Eric Evans",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/ebooks/ddd.pdf",
            }
        ],
    }
    create_response = client.post("/ebooks", json=create_payload, headers=headers)
    created_id = create_response.json()["id"]

    response = client.get(f"/ebooks/{created_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == created_id
    assert response.json()["title"] == "Domain-Driven Design"


def test_user_libraries_are_isolated(client: TestClient) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")
    shared_payload = {
        "title": "Refactoring",
        "author_name": "Martin Fowler",
        "isbn_13": "9780134757599",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/ebooks/refactoring.pdf",
            }
        ],
    }

    response_alice = client.post("/ebooks", json=shared_payload, headers=alice_headers)
    response_bob = client.post("/ebooks", json=shared_payload, headers=bob_headers)

    assert response_alice.status_code == 201
    assert response_bob.status_code == 201

    list_alice = client.get("/ebooks", headers=alice_headers)
    list_bob = client.get("/ebooks", headers=bob_headers)
    list_default = client.get("/ebooks", headers=_auth_headers(client, username="default"))

    alice_payload = list_alice.json()
    bob_payload = list_bob.json()
    default_payload = list_default.json()

    assert len(_list_items(alice_payload)) == 1
    assert _list_items(alice_payload)[0]["owner_username"] == "alice"

    assert len(_list_items(bob_payload)) == 1
    assert _list_items(bob_payload)[0]["owner_username"] == "bob"

    assert default_payload["items"] == []

    alice_book_id = _list_items(alice_payload)[0]["id"]
    bob_view_of_alice = client.get(f"/ebooks/{alice_book_id}", headers=bob_headers)
    assert bob_view_of_alice.status_code == 404


def test_query_username_does_not_override_token_identity(client: TestClient) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")
    payload = {
        "title": "Token Identity Test",
        "author_name": "Identity Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/ebooks/token-identity.pdf",
            }
        ],
    }

    create_response = client.post("/ebooks?username=bob", json=payload, headers=alice_headers)

    assert create_response.status_code == 201
    assert create_response.json()["owner_username"] == "alice"

    list_as_alice = client.get("/ebooks", headers=alice_headers)
    list_as_bob = client.get("/ebooks", headers=bob_headers)

    assert len(_list_items(list_as_alice.json())) == 1
    assert list_as_bob.json()["items"] == []


def test_list_ebooks_supports_filters(client: TestClient) -> None:
    headers = _auth_headers(client, username="alice")
    books = [
        {
            "title": "Clean Code",
            "author_name": "Robert Martin",
            "genre_names": ["Programming"],
            "publishing_year": 2008,
            "has_adaptation": False,
            "files": [
                {
                    "media_type": "ebook",
                    "file_format": "pdf",
                    "storage_path": "uploads/ebooks/clean-code.pdf",
                }
            ],
        },
        {
            "title": "The Martian",
            "author_name": "Andy Weir",
            "genre_names": ["Science Fiction"],
            "publishing_year": 2011,
            "has_adaptation": True,
            "files": [
                {
                    "media_type": "ebook",
                    "file_format": "epub",
                    "storage_path": "uploads/ebooks/the-martian.epub",
                }
            ],
        },
        {
            "title": "Domain Modeling Made Functional",
            "author_name": "Scott Wlaschin",
            "genre_names": ["Programming"],
            "publishing_year": 2018,
            "has_adaptation": False,
            "files": [
                {
                    "media_type": "ebook",
                    "file_format": "pdf",
                    "storage_path": "uploads/ebooks/domain-modeling.pdf",
                }
            ],
        },
    ]

    for payload in books:
        response = client.post("/ebooks", json=payload, headers=headers)
        assert response.status_code == 201

    by_title = client.get("/ebooks?title=martian", headers=headers)
    assert len(_list_items(by_title.json())) == 1
    assert _list_items(by_title.json())[0]["title"] == "The Martian"

    by_author = client.get("/ebooks?author=scott", headers=headers)
    assert len(_list_items(by_author.json())) == 1
    assert _list_items(by_author.json())[0]["author_name"] == "Scott Wlaschin"

    by_category = client.get("/ebooks?category=programming", headers=headers)
    assert len(_list_items(by_category.json())) == 2

    by_year = client.get("/ebooks?publishing_year=2011", headers=headers)
    assert len(_list_items(by_year.json())) == 1
    assert _list_items(by_year.json())[0]["title"] == "The Martian"

    by_adaptation = client.get("/ebooks?has_adaptation=true", headers=headers)
    assert len(_list_items(by_adaptation.json())) == 1
    assert _list_items(by_adaptation.json())[0]["title"] == "The Martian"


def test_patch_ebook_updates_metadata(client: TestClient) -> None:
    headers = _auth_headers(client, username="alice")
    create_payload = {
        "title": "Design Patterns",
        "author_name": "Gamma",
        "genre_names": ["Software"],
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/ebooks/design-patterns.pdf",
            }
        ],
    }
    create_response = client.post("/ebooks", json=create_payload, headers=headers)
    ebook_id = create_response.json()["id"]

    patch_payload = {
        "title": "Design Patterns (Updated)",
        "author_name": "Erich Gamma",
        "genre_names": ["Software Engineering", "Architecture"],
        "has_adaptation": True,
    }
    patch_response = client.patch(f"/ebooks/{ebook_id}", json=patch_payload, headers=headers)

    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["title"] == "Design Patterns (Updated)"
    assert body["author_name"] == "Erich Gamma"
    assert sorted(body["genre_names"]) == ["Architecture", "Software Engineering"]
    assert body["has_adaptation"] is True


def test_patch_ebook_respects_user_scope(client: TestClient) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")
    create_payload = {
        "title": "Patterns of Enterprise Application Architecture",
        "author_name": "Martin Fowler",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "epub",
                "storage_path": "uploads/ebooks/poeaa.epub",
            }
        ],
    }
    create_response = client.post("/ebooks", json=create_payload, headers=alice_headers)
    ebook_id = create_response.json()["id"]

    response = client.patch(f"/ebooks/{ebook_id}", json={"title": "Should Fail"}, headers=bob_headers)

    assert response.status_code == 404


def test_delete_ebook_removes_record(client: TestClient) -> None:
    headers = _auth_headers(client)
    create_payload = {
        "title": "Working Effectively with Legacy Code",
        "author_name": "Michael Feathers",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/ebooks/legacy-code.pdf",
            }
        ],
    }
    create_response = client.post("/ebooks", json=create_payload, headers=headers)
    ebook_id = create_response.json()["id"]

    delete_response = client.delete(f"/ebooks/{ebook_id}", headers=headers)
    assert delete_response.status_code == 204

    fetch_response = client.get(f"/ebooks/{ebook_id}", headers=headers)
    assert fetch_response.status_code == 404


def test_delete_ebook_respects_user_scope(client: TestClient) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")
    create_payload = {
        "title": "Test-Driven Development",
        "author_name": "Kent Beck",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/ebooks/tdd.pdf",
            }
        ],
    }
    create_response = client.post("/ebooks", json=create_payload, headers=alice_headers)
    ebook_id = create_response.json()["id"]

    delete_response = client.delete(f"/ebooks/{ebook_id}", headers=bob_headers)
    assert delete_response.status_code == 404

    still_exists = client.get(f"/ebooks/{ebook_id}", headers=alice_headers)
    assert still_exists.status_code == 200


def test_post_ebook_rejects_non_ebook_media_type(client: TestClient) -> None:
    headers = _auth_headers(client)
    payload = {
        "title": "Invalid Media",
        "author_name": "Test Author",
        "files": [
            {
                "media_type": "audiobook",
                "file_format": "mp3",
                "storage_path": "uploads/audiobooks/invalid.mp3",
            }
        ],
    }

    response = client.post("/ebooks", json=payload, headers=headers)

    assert response.status_code == 400
    assert "media_type='ebook'" in response.json()["detail"]


def test_list_ebooks_pagination_and_sort(client: TestClient) -> None:
    headers = _auth_headers(client, username="alice")
    for title in ["Book C", "Book A", "Book B"]:
        payload = {
            "title": title,
            "author_name": "Sorter",
            "files": [
                {
                    "media_type": "ebook",
                    "file_format": "pdf",
                    "storage_path": f"uploads/ebooks/{title.replace(' ', '-').lower()}.pdf",
                }
            ],
        }
        response = client.post("/ebooks", json=payload, headers=headers)
        assert response.status_code == 201

    page_one = client.get(
        "/ebooks?page=1&page_size=2&sort_by=title&sort_dir=asc",
        headers=headers,
    )
    page_two = client.get(
        "/ebooks?page=2&page_size=2&sort_by=title&sort_dir=asc",
        headers=headers,
    )

    assert page_one.status_code == 200
    page_one_payload = page_one.json()
    page_two_payload = page_two.json()

    assert [item["title"] for item in _list_items(page_one_payload)] == ["Book A", "Book B"]
    assert page_one_payload["page"] == 1
    assert page_one_payload["page_size"] == 2
    assert page_one_payload["total_count"] == 3
    assert page_one_payload["total_pages"] == 2
    assert page_one_payload["has_next"] is True
    assert page_one_payload["has_previous"] is False

    assert page_two.status_code == 200
    assert [item["title"] for item in _list_items(page_two_payload)] == ["Book C"]
    assert page_two_payload["page"] == 2
    assert page_two_payload["has_next"] is False
    assert page_two_payload["has_previous"] is True


def test_delete_ebook_cleans_up_unreferenced_uploaded_file(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client)
    file_path = Path(settings.upload_root) / "default" / "ebooks" / "delete-cleanup.pdf"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"cleanup me")

    payload = {
        "title": "Delete Cleanup",
        "author_name": "Cleanup Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/default/ebooks/delete-cleanup.pdf",
            }
        ],
    }
    create_response = client.post("/ebooks", json=payload, headers=headers)
    ebook_id = create_response.json()["id"]

    delete_response = client.delete(f"/ebooks/{ebook_id}", headers=headers)

    assert delete_response.status_code == 204
    assert not file_path.exists()


def test_patch_replace_file_cleans_old_uploaded_file(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client, username="alice")
    old_file = Path(settings.upload_root) / "alice" / "ebooks" / "old-file.pdf"
    new_file = Path(settings.upload_root) / "alice" / "ebooks" / "new-file.pdf"
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.write_bytes(b"old")
    new_file.write_bytes(b"new")

    payload = {
        "title": "Replace File",
        "author_name": "Cleanup Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "pdf",
                "storage_path": "uploads/alice/ebooks/old-file.pdf",
            }
        ],
    }
    create_response = client.post("/ebooks", json=payload, headers=headers)
    ebook_id = create_response.json()["id"]

    patch_payload = {
        "replace_file": {
            "media_type": "ebook",
            "file_format": "pdf",
            "storage_path": "uploads/alice/ebooks/new-file.pdf",
            "checksum_sha256": "abc123checksum",
        }
    }
    patch_response = client.patch(
        f"/ebooks/{ebook_id}",
        json=patch_payload,
        headers=headers,
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["files"][0]["storage_path"] == "uploads/alice/ebooks/new-file.pdf"
    assert patch_response.json()["files"][0]["checksum_sha256"] == "abc123checksum"
    assert not old_file.exists()
    assert new_file.exists()


def test_create_ebook_auto_extracts_epub_cover(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client, username="alice")
    cover_bytes = b"\x89PNG\r\n\x1a\nmock-cover-bytes"
    epub_path = Path(settings.upload_root) / "alice" / "ebooks" / "cover-source.epub"
    _create_minimal_epub_with_cover(epub_path, cover_bytes)

    payload = {
        "title": "Cover Source",
        "author_name": "Cover Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "epub",
                "storage_path": "uploads/alice/ebooks/cover-source.epub",
            }
        ],
    }

    response = client.post("/ebooks", json=payload, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["cover_art_path"] is not None
    assert body["cover_art_path"].startswith("uploads/alice/covers/")

    stored_cover_name = Path(body["cover_art_path"]).name
    stored_cover_path = Path(settings.upload_root) / "alice" / "covers" / stored_cover_name
    assert stored_cover_path.exists()
    assert stored_cover_path.read_bytes() == cover_bytes


def test_get_ebook_cover_endpoint_returns_cover_and_enforces_scope(client: TestClient, upload_settings: Path) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")

    cover_path = Path(settings.upload_root) / "alice" / "covers" / "scope-cover.jpg"
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    expected_bytes = b"\xff\xd8\xffmock-jpeg"
    cover_path.write_bytes(expected_bytes)

    payload = {
        "title": "Scope Cover",
        "author_name": "Scope Author",
        "cover_art_path": "uploads/alice/covers/scope-cover.jpg",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "epub",
                "storage_path": "uploads/alice/ebooks/scope-cover.epub",
            }
        ],
    }
    create_response = client.post("/ebooks", json=payload, headers=alice_headers)
    ebook_id = create_response.json()["id"]

    alice_cover = client.get(f"/ebooks/{ebook_id}/cover", headers=alice_headers)
    assert alice_cover.status_code == 200
    assert alice_cover.content == expected_bytes

    bob_cover = client.get(f"/ebooks/{ebook_id}/cover", headers=bob_headers)
    assert bob_cover.status_code == 404


def test_get_ebook_download_returns_attachment(client: TestClient, upload_settings: Path) -> None:
    headers = _auth_headers(client, username="alice")
    ebook_path = Path(settings.upload_root) / "alice" / "ebooks" / "download-target.epub"
    ebook_path.parent.mkdir(parents=True, exist_ok=True)
    expected_bytes = b"PK\x03\x04mock-epub-content"
    ebook_path.write_bytes(expected_bytes)

    payload = {
        "title": "Download Target",
        "author_name": "Download Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "epub",
                "storage_path": "uploads/alice/ebooks/download-target.epub",
            }
        ],
    }
    create_response = client.post("/ebooks", json=payload, headers=headers)
    ebook_id = create_response.json()["id"]

    download_response = client.get(f"/ebooks/{ebook_id}/download", headers=headers)

    assert download_response.status_code == 200
    assert download_response.content == expected_bytes
    assert "attachment" in download_response.headers.get("content-disposition", "")
    assert "Download_Target.epub" in download_response.headers.get("content-disposition", "")


def test_get_ebook_download_enforces_user_scope(client: TestClient, upload_settings: Path) -> None:
    alice_headers = _auth_headers(client, username="alice")
    bob_headers = _auth_headers(client, username="bob")

    ebook_path = Path(settings.upload_root) / "alice" / "ebooks" / "scope-download.epub"
    ebook_path.parent.mkdir(parents=True, exist_ok=True)
    ebook_path.write_bytes(b"PK\x03\x04scope-content")

    payload = {
        "title": "Scope Download",
        "author_name": "Scope Author",
        "files": [
            {
                "media_type": "ebook",
                "file_format": "epub",
                "storage_path": "uploads/alice/ebooks/scope-download.epub",
            }
        ],
    }
    create_response = client.post("/ebooks", json=payload, headers=alice_headers)
    ebook_id = create_response.json()["id"]

    forbidden_response = client.get(f"/ebooks/{ebook_id}/download", headers=bob_headers)
    assert forbidden_response.status_code == 404
