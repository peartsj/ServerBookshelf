from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import resolve_active_username
from app.db.models.entities import Book, Genre, User
from app.db.session import get_db
from app.schemas.categories import CategoryCreate, CategoryRead

router = APIRouter(tags=["categories"])


def _get_user(db: Session, username: str) -> User | None:
    normalized = username.strip().lower()
    return db.scalar(select(User).where(User.username == normalized))


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> list[CategoryRead]:
    user = _get_user(db, username)
    if user is None:
        return []

    query = (
        select(Genre)
        .join(Genre.books)
        .where(Book.user_id == user.id)
        .order_by(Genre.name.asc())
        .distinct()
    )
    genres = list(db.scalars(query).all())
    return [CategoryRead(id=genre.id, name=genre.name) for genre in genres]


@router.post("/categories", response_model=CategoryRead)
def create_category(
    payload: CategoryCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> CategoryRead:
    existing = db.scalar(select(Genre).where(Genre.name == payload.name))
    if existing is not None:
        return CategoryRead(id=existing.id, name=existing.name)

    genre = Genre(name=payload.name)
    db.add(genre)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name already exists") from exc

    db.refresh(genre)
    response.status_code = status.HTTP_201_CREATED
    return CategoryRead(id=genre.id, name=genre.name)


@router.post("/ebooks/{ebook_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_category_to_ebook(
    ebook_id: int,
    category_id: int,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> Response:
    user = _get_user(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    book = db.scalar(select(Book).where(Book.id == ebook_id, Book.user_id == user.id))
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    category = db.scalar(select(Genre).where(Genre.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category not in book.genres:
        book.genres.append(category)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/ebooks/{ebook_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category_from_ebook(
    ebook_id: int,
    category_id: int,
    username: str = Depends(resolve_active_username),
    db: Session = Depends(get_db),
) -> Response:
    user = _get_user(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    book = db.scalar(select(Book).where(Book.id == ebook_id, Book.user_id == user.id))
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found")

    category = db.scalar(select(Genre).where(Genre.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category in book.genres:
        book.genres.remove(category)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
