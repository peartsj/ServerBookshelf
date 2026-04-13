from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.entities import BookFile


def _resolve_uploaded_path(storage_path: str) -> Path | None:
    upload_root = Path(settings.upload_root).resolve()

    normalized = storage_path.replace("\\", "/")
    if normalized.startswith("uploads/"):
        normalized = normalized[len("uploads/") :]

    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = upload_root / candidate

    resolved = candidate.resolve()
    if not resolved.is_relative_to(upload_root):
        return None

    return resolved


def delete_file_if_unreferenced(db: Session, storage_path: str) -> bool:
    references = db.scalar(select(func.count(BookFile.id)).where(BookFile.storage_path == storage_path))
    if references and references > 0:
        return False

    resolved_path = _resolve_uploaded_path(storage_path)
    if resolved_path is None or not resolved_path.exists():
        return False

    resolved_path.unlink(missing_ok=True)

    upload_root = Path(settings.upload_root).resolve()
    parent = resolved_path.parent
    while parent != upload_root and parent.exists():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent

    return True
