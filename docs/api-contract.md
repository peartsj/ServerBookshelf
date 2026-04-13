# Backend API Contract Tracker

This file is the source of truth for frontend/backend consistency.

## Implemented

- [x] `GET /health`
- [x] `POST /auth/register`
- [x] `POST /auth/login`
- [x] `GET /auth/me`
- [x] `GET /ebooks`
- [x] `GET /ebooks/{id}`
- [x] `GET /ebooks/{id}/cover`
- [x] `GET /ebooks/{id}/download`
- [x] `POST /ebooks`
- [x] `PATCH /ebooks/{id}`
- [x] `DELETE /ebooks/{id}`
- [x] `GET /categories`
- [x] `POST /categories`
- [x] `POST /ebooks/{id}/categories/{categoryId}`
- [x] `DELETE /ebooks/{id}/categories/{categoryId}`
- [x] `POST /uploads/ebook-file`

## Planned

- [ ] Persistent auth token revocation/session invalidation

## Current user scoping approach

- `POST /auth/register` requires `username`, `password`, and `password_confirmation`.
- `POST /auth/login` requires `username` and `password`.
- Protected endpoints require `Authorization: Bearer <token>`.
- Header/query username fallbacks are disabled for protected routes.
- Libraries are isolated by user and cannot read each other's books.

## Ebook list filters

- `GET /ebooks` supports optional query parameters:
- `title` (contains match)
- `author` (contains match)
- `category` (contains match)
- `publishing_year` (exact match)
- `has_adaptation` (`true` or `false`)
- `page` (1-based)
- `page_size` (1-100)
- `sort_by` (`created_at`, `title`, `author`, `publishing_year`)
- `sort_dir` (`asc`, `desc`)

`GET /ebooks` response shape:

- `items`: array of `EbookRead`
- `page`: current 1-based page
- `page_size`: requested page size
- `total_count`: total matching books
- `total_pages`: computed from `total_count` and `page_size`
- `has_next`: whether a next page exists
- `has_previous`: whether a previous page exists

## Categories notes

- `POST /categories` creates a category if missing, or returns the existing one if the name already exists.
- `GET /categories` returns categories attached to books in the scoped user library.

## Upload-first flow contract

1. `POST /uploads/ebook-file` (multipart): returns `storage_path`, `file_format`, `size_bytes`, and `checksum_sha256`.
2. Upload validation accepts EPUB only (`.epub`), enforces content-type allowlist checks, rejects empty files, and validates ZIP/EPUB signature (`PK`).
3. `POST /ebooks`: send one `files` entry with the returned upload metadata.
4. Optional: create categories and attach using `/categories` and `/ebooks/{id}/categories/{categoryId}`.
5. During `POST /ebooks`, if the ebook file is EPUB and `cover_art_path` is not provided, backend attempts to extract the EPUB cover image automatically.
6. Frontend can fetch cover bytes from `GET /ebooks/{id}/cover` (bearer token required, user-scoped).
7. Frontend can download ebook bytes from `GET /ebooks/{id}/download` (bearer token required, user-scoped, attachment response).
