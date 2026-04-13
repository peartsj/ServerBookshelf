# Frontend

Minimal static frontend for the staged add-book workflow and basic library management.

## Run locally

From the `frontend/` directory:

```bash
c:/python314/python.exe -m http.server 4409
```

Then open `http://localhost:4409`.

## Run with Docker Compose

From the repo root:

```bash
docker compose up --build
```

Then open `http://localhost:4409`.

In Docker mode, the frontend serves API calls through same-origin `/api` proxying to the backend container. This avoids browser CORS/network-origin issues on server deployments.

## Current flow

1. Auth screen supports register via `POST /auth/register` (username + password + password confirmation) and login via `POST /auth/login` (username + password).
2. After login, library screen loads with filter/sort controls and an `Add New Book` button.
3. Add book opens a modal dialog.
4. Upload EPUB file through `POST /uploads/ebook-file`; the UI shows uploaded filename, size, and SHA-256 checksum after success.
5. Fill metadata and create ebook via `POST /ebooks`; category input supports autocomplete from known categories and quick-add category chips.
6. Create/attach categories via `/categories` and `/ebooks/{id}/categories/{categoryId}`.

## Current library actions

- List ebooks for the authenticated user
- Show EPUB cover thumbnails on the right side of each list row (when available)
- Open a dedicated details popout for a selected book (includes full description and key metadata)
- Download ebook files directly from each library row via an authenticated `Download` button
- Filter ebooks by title, author, category, and year
- Paginate and sort ebook list
- Edit ebook metadata (title, author, year, description)
- Delete ebooks
- Attach and detach categories
- Show file metadata in list (format and optional size)
- Category autocomplete and quick-add chips with recent category memory
- EPUB-only upload target for final MVP scope

Identity behavior:

- Register requires username + password + password confirmation.
- Login requires both username and password.
- Protected requests always send `Authorization: Bearer <token>`.
- Logging out clears token and returns to the login screen.

## Files

- `index.html` UI layout
- `styles.css` styling
- `api.js` frontend API helpers
- `app.js` staged flow wiring
- `env.js` default runtime API config for local static hosting
- `Dockerfile` + `docker-entrypoint.sh` for frontend container runtime config
