from pathlib import Path
import hashlib
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import resolve_active_username
from app.core.config import settings
from app.db.models.entities import User
from app.db.session import get_db
from app.schemas.uploads import UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_EBOOK_EXTENSIONS = {".epub"}

ALLOWED_CONTENT_TYPES_BY_EXTENSION = {
    ".epub": {"application/epub+zip", "application/zip", "application/octet-stream"},
}


def _validate_file_signature(file_extension: str, first_chunk: bytes) -> None:
    if file_extension == ".epub" and not first_chunk.startswith(b"PK"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid EPUB archive")


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _get_or_create_user(db: Session, username: str) -> User:
    normalized = _normalize_username(username)
    existing = db.scalar(select(User).where(User.username == normalized))
    if existing is not None:
        return existing

    created = User(username=normalized)
    db.add(created)
    db.commit()
    db.refresh(created)
    return created


@router.post("/ebook-file", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_ebook_file(
    file: UploadFile = File(...),
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> UploadResponse:
    original_name = file.filename or "uploaded-file"
    file_extension = Path(original_name).suffix.lower()
    if file_extension not in ALLOWED_EBOOK_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{file_extension}'. Allowed: {sorted(ALLOWED_EBOOK_EXTENSIONS)}",
        )

    allowed_content_types = ALLOWED_CONTENT_TYPES_BY_EXTENSION.get(file_extension, {"application/octet-stream"})
    if file.content_type and file.content_type.lower() not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type '{file.content_type}' for extension '{file_extension}'",
        )

    user = _get_or_create_user(db, username)
    upload_dir = Path(settings.upload_root) / user.username / "ebooks"
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}{file_extension}"
    destination = upload_dir / stored_filename

    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    bytes_written = 0
    hasher = hashlib.sha256()
    first_chunk: bytes | None = None

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break

                if first_chunk is None:
                    first_chunk = chunk

                bytes_written += len(chunk)
                if bytes_written > max_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds max size of {settings.max_upload_size_mb} MB",
                    )

                hasher.update(chunk)
                output.write(chunk)

        if first_chunk is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

        _validate_file_signature(file_extension, first_chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    storage_path = str(Path("uploads") / user.username / "ebooks" / stored_filename).replace("\\", "/")
    return UploadResponse(
        original_filename=original_name,
        stored_filename=stored_filename,
        storage_path=storage_path,
        file_format=file_extension.removeprefix("."),
        size_bytes=bytes_written,
        checksum_sha256=hasher.hexdigest(),
        owner_username=user.username,
    )
