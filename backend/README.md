# Backend (FastAPI)

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 4408
```

## Run tests

```bash
pytest
```

Includes staged integration coverage for upload -> create -> category attach/detach.

## Notes

- Tables are created automatically on startup for initial development.
- Schema supports `ebook` and `audiobook` media types via `book_files.media_type`.

## Current endpoints

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /ebooks`
- `GET /ebooks/{id}`
- `GET /ebooks/{id}/cover`
- `GET /ebooks/{id}/download`
- `POST /ebooks`
- `PATCH /ebooks/{id}`
- `DELETE /ebooks/{id}`
- `GET /categories`
- `POST /categories`
- `POST /ebooks/{id}/categories/{categoryId}`
- `DELETE /ebooks/{id}/categories/{categoryId}`
- `POST /uploads/ebook-file` (multipart form field: `file`)

User scoping:

- `POST /auth/register` requires `username`, `password`, and `password_confirmation`.
- `POST /auth/login` requires `username` and `password`.
- Protected endpoints require `Authorization: Bearer <token>`.
- Username header/query fallbacks are disabled for protected routes.

`GET /ebooks` filter query params:

- `title`
- `author`
- `category`
- `publishing_year`
- `has_adaptation`
- `page`
- `page_size`
- `sort_by`
- `sort_dir`

`GET /ebooks` response envelope:

- `items`
- `page`
- `page_size`
- `total_count`
- `total_pages`
- `has_next`
- `has_previous`

Upload validation:

- Allowed ebook extension: `.epub`
- EPUB content-type allowlist checks
- EPUB signature validation (`PK`)
- Empty uploads are rejected
- Default max upload size: `25 MB` (configurable via `max_upload_size_mb`)
- In Docker Compose deployments, set `MAX_UPLOAD_SIZE_MB` in project `.env` (default `25`).
- Upload responses include `checksum_sha256` for file integrity tracking
- `POST /ebooks` attempts to auto-extract EPUB cover art when possible (if `cover_art_path` is omitted)
- `GET /ebooks/{id}/cover` returns the user-scoped cover image bytes for frontend thumbnail rendering
- `GET /ebooks/{id}/download` returns the user-scoped ebook file as an attachment download

Development note:

- CORS allowlist is configured by `cors_allow_origins` (defaults to local frontend origins).
- Uploaded ebook files are deleted from disk when no longer referenced (ebook delete or file replacement).
