# CS 452 Final Project: Self-Hosted Bookshelf

This repository contains a split frontend/backend project for a self-hosted bookshelf service.

## Folders

- `backend/` Python FastAPI backend, database models, tests
- `frontend/` Minimal web UI scaffold (upload/create/edit/delete/filter)
- `docs/` API contract and project notes

## Quick Start

```bash
docker compose up --build
```

## Docker Runbook (Step-by-step)

Use this when you want a clean local run with containers.

1) Prerequisites

- Install Docker Desktop.
- In Docker Desktop settings, ensure Docker Compose V2 is enabled.
- Make sure ports `4408` and `4409` are free.

2) Start from project root

```bash
cd "c:/Users/spenc/CS projects/CS 452 Final Project"
```

3) Build and run containers

```bash
docker compose up --build
```

4) Open the app

- Frontend: http://localhost:4409
- Backend API: http://localhost:4408
- Health check: http://localhost:4408/health

5) First-use test path (EPUB-only)

- Login with username + password.
- Upload one `.epub` file in Add Book.
- Fill title/author and create record.
- Confirm the book appears in the library list.
- Click `Download` on the book row and confirm the ebook downloads.

6) Run detached (optional)

```bash
docker compose up --build -d
docker compose ps
```

7) View logs (optional)

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

8) Stop services

```bash
docker compose down
```

9) Stop and remove volumes (only if you want a clean reset)

This clears persisted local DB/upload state.

```bash
docker compose down -v
```

Data persistence note:

- App data now lives in Docker named volumes: `bookshelf_data` (database) and `bookshelf_uploads` (uploaded files).
- Rebuilding or updating containers with `docker compose up --build -d` keeps your library data.
- Do not run `docker compose down -v` unless you intentionally want to wipe the library.

## Deploy To Home Server Over SSH (Easiest Path)

The easiest reliable workflow is: copy the project once with `rsync` over SSH, then update in place and rebuild.

1) Prepare the server (one-time)

- SSH into the server.
- Install Docker Engine + Docker Compose plugin.
- Create an app directory, for example `/opt/bookshelf`.

2) Copy project files from your PC to server (one-time or on each update)

Run this from your local machine (PowerShell, Git Bash, or WSL):

```bash
rsync -avz --delete \
	--exclude '.git' \
	--exclude '.env' \
	--exclude '__pycache__' \
	--exclude '.pytest_cache' \
	"/c/Users/spenc/CS projects/CS 452 Final Project/" \
	youruser@YOUR_SERVER_IP:/opt/bookshelf/
```

If `rsync` is unavailable, use `scp -r` as fallback:

```bash
scp -r "c:/Users/spenc/CS projects/CS 452 Final Project" youruser@YOUR_SERVER_IP:/opt/bookshelf
```

3) Set the frontend API URL for server clients

On the server, create `/opt/bookshelf/.env`:

```bash
cat >/opt/bookshelf/.env <<'EOF'
FRONTEND_API_BASE_URL=http://YOUR_SERVER_IP:4408
EOF
```

Use a LAN IP or DNS name that browsers on your network can reach.

4) Start the stack on the server

```bash
cd /opt/bookshelf
docker compose up --build -d
docker compose ps
```

5) Validate

```bash
curl -sS http://localhost:4408/health
```

Then open `http://YOUR_SERVER_IP:4409` from another machine.

6) Update later without losing library data

- Re-run the same `rsync` command from local to server.
- SSH to server and run:

```bash
cd /opt/bookshelf
docker compose up --build -d
```

Your library remains because data is stored in named volumes.

7) Optional backup commands (recommended)

```bash
DATA_VOL=$(docker volume ls --format '{{.Name}}' | grep 'bookshelf_data$' | head -n1)
UPLOAD_VOL=$(docker volume ls --format '{{.Name}}' | grep 'bookshelf_uploads$' | head -n1)

docker run --rm -v "$DATA_VOL":/from -v "$PWD":/to alpine tar czf /to/bookshelf_data_backup.tgz -C /from .
docker run --rm -v "$UPLOAD_VOL":/from -v "$PWD":/to alpine tar czf /to/bookshelf_uploads_backup.tgz -C /from .
```

To restore, untar back into the same mounted volumes.

## Troubleshooting

- Port already in use:
	- Change host-side mapping in `docker-compose.yml`, then rerun `docker compose up --build`.
- Frontend opens but API calls fail:
	- Verify backend container is healthy in `docker compose ps`.
	- Check backend logs with `docker compose logs -f backend`.
- Upload rejected:
	- Current project scope is EPUB-only; upload `.epub` files.

Backend checks:

- `GET http://localhost:4408/health`
- `POST http://localhost:4408/auth/register` with JSON body `{ "username": "default", "password": "your-password", "password_confirmation": "your-password" }`
- `POST http://localhost:4408/auth/login` with JSON body `{ "username": "default", "password": "your-password" }`
- `POST http://localhost:4408/uploads/ebook-file` with header `Authorization: Bearer <token>` (multipart `file`, EPUB only)
- `GET http://localhost:4408/ebooks/{id}/download` with header `Authorization: Bearer <token>` (download ebook attachment)

Frontend scaffold:

- `http://localhost:4409`
- Or serve `frontend/` as static files manually (see `frontend/README.md`).
