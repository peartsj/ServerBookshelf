from typing import Literal
import mimetypes
from pathlib import Path
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import asc, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import resolve_active_username
from app.core.config import settings
from app.db.models.entities import Author, Book, BookFile, Genre, MediaType, Publisher, Series, User
from app.db.session import get_db
from app.schemas.ebooks import EbookCreate, EbookFileRead, EbookListResponse, EbookRead, EbookUpdate
from app.services.epub_cover import read_epub_cover
from app.services.file_storage import delete_file_if_unreferenced

router = APIRouter(prefix="/ebooks", tags=["ebooks"])


def _get_or_create_named_entity(db: Session, model, name: str):
    normalized = name.strip()
    existing = db.scalar(select(model).where(model.name == normalized))
    if existing is not None:
        return existing

    created = model(name=normalized)
    db.add(created)
    db.flush()
    return created


def _get_or_create_user(db: Session, username: str) -> User:
    normalized = username.strip().lower()
    existing = db.scalar(select(User).where(User.username == normalized))
    if existing is not None:
        return existing

    created = User(username=normalized)
    db.add(created)
    db.flush()
    return created


def _get_user(db: Session, username: str) -> User | None:
    normalized = username.strip().lower()
    return db.scalar(select(User).where(User.username == normalized))


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


def _build_download_filename(title: str, file_format: str, fallback_suffix: str) -> str:
    safe_title = re.sub(r"[^A-Za-z0-9 _-]", "_", title).strip()
    safe_title = re.sub(r"\s+", "_", safe_title)
    if not safe_title:
        safe_title = "ebook"

    extension = file_format.strip().lower().lstrip(".")
    if extension:
        return f"{safe_title}.{extension}"

    normalized_suffix = fallback_suffix.strip()
    if normalized_suffix and not normalized_suffix.startswith("."):
        normalized_suffix = f".{normalized_suffix}"

    return f"{safe_title}{normalized_suffix}" if normalized_suffix else safe_title


def _auto_extract_epub_cover(payload: EbookCreate, owner_username: str) -> str | None:
    if payload.cover_art_path:
        return payload.cover_art_path

    ebook_file = next((file for file in payload.files if file.media_type == MediaType.EBOOK), None)
    if ebook_file is None or ebook_file.file_format.lower() != "epub":
        return None

    source_path = _resolve_uploaded_path(ebook_file.storage_path)
    if source_path is None:
        return None

    cover = read_epub_cover(source_path)
    if cover is None:
        return None

    cover_dir = Path(settings.upload_root) / owner_username / "covers"
    cover_dir.mkdir(parents=True, exist_ok=True)

    cover_filename = f"{uuid4().hex}{cover.extension}"
    destination = cover_dir / cover_filename
    destination.write_bytes(cover.content)

    return str(Path("uploads") / owner_username / "covers" / cover_filename).replace("\\", "/")


def _serialize_book(book: Book) -> EbookRead:
    ebook_files = [
        EbookFileRead(
            id=file.id,
            media_type=file.media_type,
            file_format=file.file_format,
            storage_path=file.storage_path,
            file_size_bytes=file.file_size_bytes,
            checksum_sha256=file.checksum_sha256,
        )
        for file in book.files
        if file.media_type == MediaType.EBOOK
    ]

    return EbookRead(
        id=book.id,
        owner_username=book.user.username,
        title=book.title,
        author_name=book.author.name,
        publisher_name=book.publisher.name if book.publisher else None,
        genre_names=sorted([genre.name for genre in book.genres]),
        description=book.description,
        publishing_year=book.publishing_year,
        series_name=book.series.name if book.series else None,
        series_position=book.series_position,
        has_adaptation=book.has_adaptation,
        cover_art_path=book.cover_art_path,
        isbn_13=book.isbn_13,
        language_code=book.language_code,
        files=ebook_files,
    )


@router.get("", response_model=EbookListResponse)
def list_ebooks(
    username: str = Depends(resolve_active_username),
    title: str | None = Query(default=None),
    author: str | None = Query(default=None),
    category: str | None = Query(default=None),
    publishing_year: int | None = Query(default=None, ge=0, le=3000),
    has_adaptation: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: Literal["created_at", "title", "author", "publishing_year"] = Query(default="created_at"),
    sort_dir: Literal["asc", "desc"] = Query(default="desc"),
    db: Session = Depends(get_db),
) -> EbookListResponse:
    user = _get_user(db, username)
    if user is None:
        return EbookListResponse(
            items=[],
            page=page,
            page_size=page_size,
            total_count=0,
            total_pages=0,
            has_next=False,
            has_previous=page > 1,
        )

    base_query = (
        select(Book.id)
        .join(Book.files)
        .where(Book.user_id == user.id, BookFile.media_type == MediaType.EBOOK)
    )

    needs_author_join = bool(author) or sort_by == "author"
    needs_category_join = bool(category)

    if needs_author_join:
        base_query = base_query.join(Book.author)

    if needs_category_join:
        base_query = base_query.join(Book.genres)

    if title:
        base_query = base_query.where(Book.title.ilike(f"%{title.strip()}%"))

    if author:
        base_query = base_query.where(Author.name.ilike(f"%{author.strip()}%"))

    if category:
        base_query = base_query.where(Genre.name.ilike(f"%{category.strip()}%"))

    if publishing_year is not None:
        base_query = base_query.where(Book.publishing_year == publishing_year)

    if has_adaptation is not None:
        base_query = base_query.where(Book.has_adaptation == has_adaptation)

    sort_map = {
        "created_at": Book.created_at,
        "title": Book.title,
        "author": Author.name,
        "publishing_year": Book.publishing_year,
    }
    sort_expr = sort_map[sort_by]
    order_by_clause = asc(sort_expr) if sort_dir == "asc" else desc(sort_expr)

    total_count = db.scalar(select(func.count()).select_from(base_query.distinct().subquery())) or 0
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    offset = (page - 1) * page_size
    page_book_ids = list(
        db.scalars(base_query.distinct().order_by(order_by_clause).offset(offset).limit(page_size)).all()
    )

    page_books: list[Book] = []
    if page_book_ids:
        books = db.scalars(
            select(Book)
            .where(Book.id.in_(page_book_ids))
            .options(
                selectinload(Book.user),
                selectinload(Book.author),
                selectinload(Book.publisher),
                selectinload(Book.series),
                selectinload(Book.genres),
                selectinload(Book.files),
            )
        ).all()
        books_by_id = {book.id: book for book in books}
        page_books = [books_by_id[book_id] for book_id in page_book_ids if book_id in books_by_id]

    return EbookListResponse(
        items=[_serialize_book(book) for book in page_books],
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.get("/{ebook_id}", response_model=EbookRead)
def get_ebook(
    ebook_id: int,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> EbookRead:
    user = _get_user(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    query = (
        select(Book)
        .join(Book.files)
        .where(
            Book.id == ebook_id,
            Book.user_id == user.id,
            BookFile.media_type == MediaType.EBOOK,
        )
        .options(
            selectinload(Book.user),
            selectinload(Book.author),
            selectinload(Book.publisher),
            selectinload(Book.series),
            selectinload(Book.genres),
            selectinload(Book.files),
        )
        .distinct()
    )

    book = db.scalar(query)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    return _serialize_book(book)


@router.post("", response_model=EbookRead, status_code=status.HTTP_201_CREATED)
def create_ebook(
    payload: EbookCreate,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> EbookRead:
    if any(file.media_type != MediaType.EBOOK for file in payload.files):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="/ebooks only accepts files with media_type='ebook'",
        )

    user = _get_or_create_user(db, username)
    author = _get_or_create_named_entity(db, Author, payload.author_name)
    publisher = _get_or_create_named_entity(db, Publisher, payload.publisher_name) if payload.publisher_name else None
    series = _get_or_create_named_entity(db, Series, payload.series_name) if payload.series_name else None

    auto_cover_path = _auto_extract_epub_cover(payload, user.username)

    book = Book(
        title=payload.title,
        description=payload.description,
        publishing_year=payload.publishing_year,
        has_adaptation=payload.has_adaptation,
        cover_art_path=auto_cover_path,
        isbn_13=payload.isbn_13,
        language_code=payload.language_code,
        series_position=payload.series_position,
        user_id=user.id,
        author_id=author.id,
        publisher_id=publisher.id if publisher else None,
        series_id=series.id if series else None,
    )
    db.add(book)
    db.flush()

    for genre_name in payload.genre_names:
        genre = _get_or_create_named_entity(db, Genre, genre_name)
        book.genres.append(genre)

    for file_payload in payload.files:
        db.add(
            BookFile(
                book_id=book.id,
                media_type=file_payload.media_type,
                file_format=file_payload.file_format,
                storage_path=file_payload.storage_path,
                file_size_bytes=file_payload.file_size_bytes,
                checksum_sha256=file_payload.checksum_sha256,
                duration_seconds=None,
            )
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ebook could not be created due to conflicting unique metadata in this user library",
        ) from exc

    created_book = db.scalar(
        select(Book)
        .where(Book.id == book.id)
        .options(
            selectinload(Book.user),
            selectinload(Book.author),
            selectinload(Book.publisher),
            selectinload(Book.series),
            selectinload(Book.genres),
            selectinload(Book.files),
        )
    )
    if created_book is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load created ebook")

    return _serialize_book(created_book)


@router.get("/{ebook_id}/cover")
def get_ebook_cover(
    ebook_id: int,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> Response:
    user = _get_user(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover image not found")

    book = db.scalar(select(Book).where(Book.id == ebook_id, Book.user_id == user.id))
    if book is None or not book.cover_art_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover image not found")

    resolved_path = _resolve_uploaded_path(book.cover_art_path)
    if resolved_path is None or not resolved_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover image not found")

    media_type = mimetypes.guess_type(str(resolved_path))[0] or "application/octet-stream"
    return FileResponse(path=str(resolved_path), media_type=media_type)


@router.get("/{ebook_id}/download")
def download_ebook_file(
    ebook_id: int,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> Response:
    user = _get_user(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook file not found")

    book = db.scalar(
        select(Book)
        .where(Book.id == ebook_id, Book.user_id == user.id)
        .options(selectinload(Book.files))
    )
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook file not found")

    ebook_file = next((item for item in book.files if item.media_type == MediaType.EBOOK), None)
    if ebook_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook file not found")

    resolved_path = _resolve_uploaded_path(ebook_file.storage_path)
    if resolved_path is None or not resolved_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook file not found")

    media_type = mimetypes.guess_type(str(resolved_path))[0] or "application/octet-stream"
    download_name = _build_download_filename(book.title, ebook_file.file_format, resolved_path.suffix)

    return FileResponse(path=str(resolved_path), media_type=media_type, filename=download_name)


@router.patch("/{ebook_id}", response_model=EbookRead)
def update_ebook(
    ebook_id: int,
    payload: EbookUpdate,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> EbookRead:
    user = _get_user(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    book = db.scalar(
        select(Book)
        .where(Book.id == ebook_id, Book.user_id == user.id)
        .options(
            selectinload(Book.user),
            selectinload(Book.author),
            selectinload(Book.publisher),
            selectinload(Book.series),
            selectinload(Book.genres),
            selectinload(Book.files),
        )
    )
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    updates = payload.model_dump(exclude_unset=True)
    old_storage_path_for_cleanup: str | None = None

    if "title" in updates:
        if updates["title"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title cannot be null")
        book.title = updates["title"]

    if "author_name" in updates:
        if updates["author_name"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="author_name cannot be null")
        author = _get_or_create_named_entity(db, Author, updates["author_name"])
        book.author_id = author.id

    if "publisher_name" in updates:
        publisher_name = updates["publisher_name"]
        if publisher_name is None:
            book.publisher_id = None
        else:
            publisher = _get_or_create_named_entity(db, Publisher, publisher_name)
            book.publisher_id = publisher.id

    if "series_name" in updates:
        series_name = updates["series_name"]
        if series_name is None:
            book.series_id = None
        else:
            series = _get_or_create_named_entity(db, Series, series_name)
            book.series_id = series.id

    if "genre_names" in updates:
        genre_names = updates["genre_names"] or []
        book.genres.clear()
        for genre_name in genre_names:
            genre = _get_or_create_named_entity(db, Genre, genre_name)
            book.genres.append(genre)

    if "description" in updates:
        book.description = updates["description"]
    if "publishing_year" in updates:
        book.publishing_year = updates["publishing_year"]
    if "series_position" in updates:
        book.series_position = updates["series_position"]
    if "cover_art_path" in updates:
        book.cover_art_path = updates["cover_art_path"]
    if "isbn_13" in updates:
        book.isbn_13 = updates["isbn_13"]
    if "language_code" in updates:
        book.language_code = updates["language_code"]

    if "has_adaptation" in updates:
        if updates["has_adaptation"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="has_adaptation cannot be null")
        book.has_adaptation = updates["has_adaptation"]

    if "replace_file" in updates and updates["replace_file"] is not None:
        replacement = updates["replace_file"]
        if replacement["media_type"] != MediaType.EBOOK:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="replace_file.media_type must be 'ebook'",
            )

        existing_ebook_file = next((item for item in book.files if item.media_type == MediaType.EBOOK), None)
        if existing_ebook_file is None:
            db.add(
                BookFile(
                    book_id=book.id,
                    media_type=replacement["media_type"],
                    file_format=replacement["file_format"],
                    storage_path=replacement["storage_path"],
                    file_size_bytes=replacement.get("file_size_bytes"),
                    checksum_sha256=replacement.get("checksum_sha256"),
                    duration_seconds=None,
                )
            )
        else:
            if existing_ebook_file.storage_path != replacement["storage_path"]:
                old_storage_path_for_cleanup = existing_ebook_file.storage_path

            existing_ebook_file.file_format = replacement["file_format"]
            existing_ebook_file.storage_path = replacement["storage_path"]
            existing_ebook_file.file_size_bytes = replacement.get("file_size_bytes")
            existing_ebook_file.checksum_sha256 = replacement.get("checksum_sha256")

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ebook could not be updated due to conflicting unique metadata in this user library",
        ) from exc

    if old_storage_path_for_cleanup:
        delete_file_if_unreferenced(db, old_storage_path_for_cleanup)

    updated_book = db.scalar(
        select(Book)
        .where(Book.id == book.id)
        .options(
            selectinload(Book.user),
            selectinload(Book.author),
            selectinload(Book.publisher),
            selectinload(Book.series),
            selectinload(Book.genres),
            selectinload(Book.files),
        )
    )
    if updated_book is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load updated ebook")

    return _serialize_book(updated_book)


@router.delete("/{ebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ebook(
    ebook_id: int,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> Response:
    user = _get_user(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    book = db.scalar(select(Book).where(Book.id == ebook_id, Book.user_id == user.id))
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    file_paths = [stored.storage_path for stored in book.files if stored.storage_path]

    db.delete(book)
    db.commit()

    for storage_path in file_paths:
        delete_file_if_unreferenced(db, storage_path)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
