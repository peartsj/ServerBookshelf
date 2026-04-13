import enum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class MediaType(str, enum.Enum):
    EBOOK = "ebook"
    AUDIOBOOK = "audiobook"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_salt: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), default="", nullable=False)

    books: Mapped[list["Book"]] = relationship(back_populates="user")


class Author(TimestampMixin, Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Publisher(TimestampMixin, Base):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    books: Mapped[list["Book"]] = relationship(back_populates="publisher")


class Series(TimestampMixin, Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    books: Mapped[list["Book"]] = relationship(back_populates="series")


class Genre(TimestampMixin, Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    books: Mapped[list["Book"]] = relationship(secondary="book_genres", back_populates="genres")


class Book(TimestampMixin, Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("publishing_year >= 0 AND publishing_year <= 3000", name="ck_books_publishing_year"),
        UniqueConstraint("user_id", "isbn_13", name="uq_books_user_isbn_13"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text(), nullable=True)
    publishing_year: Mapped[int] = mapped_column(Integer, nullable=True)
    has_adaptation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cover_art_path: Mapped[str] = mapped_column(String(512), nullable=True)
    isbn_13: Mapped[str] = mapped_column(String(13), index=True, nullable=True)
    language_code: Mapped[str] = mapped_column(String(8), index=True, nullable=True)
    series_position: Mapped[int] = mapped_column(Integer, nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"), index=True, nullable=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=True)

    user: Mapped["User"] = relationship(back_populates="books")
    author: Mapped["Author"] = relationship(back_populates="books")
    publisher: Mapped["Publisher"] = relationship(back_populates="books")
    series: Mapped["Series"] = relationship(back_populates="books")
    genres: Mapped[list["Genre"]] = relationship(secondary="book_genres", back_populates="books")
    files: Mapped[list["BookFile"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class BookGenre(Base):
    __tablename__ = "book_genres"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)


class BookFile(TimestampMixin, Base):
    __tablename__ = "book_files"
    __table_args__ = (
        UniqueConstraint("book_id", "storage_path", name="uq_book_files_path_per_book"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)

    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType, native_enum=False), index=True)
    file_format: Mapped[str] = mapped_column(String(32), index=True)
    storage_path: Mapped[str] = mapped_column(String(1024))

    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=True)

    book: Mapped["Book"] = relationship(back_populates="files")
