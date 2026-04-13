"""Initial schema

Revision ID: 20260408_0001
Revises:
Create Date: 2026-04-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260408_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_authors_name", "authors", ["name"], unique=True)

    op.create_table(
        "publishers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_publishers_name", "publishers", ["name"], unique=True)

    op.create_table(
        "series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_series_name", "series", ["name"], unique=True)

    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_genres_name", "genres", ["name"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("publishing_year", sa.Integer(), nullable=True),
        sa.Column("has_adaptation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cover_art_path", sa.String(length=512), nullable=True),
        sa.Column("isbn_13", sa.String(length=13), nullable=True),
        sa.Column("language_code", sa.String(length=8), nullable=True),
        sa.Column("series_position", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("authors.id"), nullable=False),
        sa.Column("publisher_id", sa.Integer(), sa.ForeignKey("publishers.id"), nullable=True),
        sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("publishing_year >= 0 AND publishing_year <= 3000", name="ck_books_publishing_year"),
        sa.UniqueConstraint("user_id", "isbn_13", name="uq_books_user_isbn_13"),
    )
    op.create_index("ix_books_title", "books", ["title"], unique=False)
    op.create_index("ix_books_user_id", "books", ["user_id"], unique=False)
    op.create_index("ix_books_author_id", "books", ["author_id"], unique=False)
    op.create_index("ix_books_publisher_id", "books", ["publisher_id"], unique=False)
    op.create_index("ix_books_series_id", "books", ["series_id"], unique=False)
    op.create_index("ix_books_isbn_13", "books", ["isbn_13"], unique=False)
    op.create_index("ix_books_language_code", "books", ["language_code"], unique=False)

    op.create_table(
        "book_genres",
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("genre_id", sa.Integer(), sa.ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
    )

    media_type_enum = sa.Enum("ebook", "audiobook", name="mediatype", native_enum=False)
    op.create_table(
        "book_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_type", media_type_enum, nullable=False),
        sa.Column("file_format", sa.String(length=32), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("book_id", "storage_path", name="uq_book_files_path_per_book"),
    )
    op.create_index("ix_book_files_book_id", "book_files", ["book_id"], unique=False)
    op.create_index("ix_book_files_media_type", "book_files", ["media_type"], unique=False)
    op.create_index("ix_book_files_file_format", "book_files", ["file_format"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_book_files_file_format", table_name="book_files")
    op.drop_index("ix_book_files_media_type", table_name="book_files")
    op.drop_index("ix_book_files_book_id", table_name="book_files")
    op.drop_table("book_files")

    op.drop_table("book_genres")

    op.drop_index("ix_books_language_code", table_name="books")
    op.drop_index("ix_books_isbn_13", table_name="books")
    op.drop_index("ix_books_series_id", table_name="books")
    op.drop_index("ix_books_publisher_id", table_name="books")
    op.drop_index("ix_books_author_id", table_name="books")
    op.drop_index("ix_books_user_id", table_name="books")
    op.drop_index("ix_books_title", table_name="books")
    op.drop_table("books")

    op.drop_index("ix_genres_name", table_name="genres")
    op.drop_table("genres")

    op.drop_index("ix_series_name", table_name="series")
    op.drop_table("series")

    op.drop_index("ix_publishers_name", table_name="publishers")
    op.drop_table("publishers")

    op.drop_index("ix_authors_name", table_name="authors")
    op.drop_table("authors")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
