from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models.entities import MediaType


class EbookFileCreate(BaseModel):
    media_type: MediaType = Field(default=MediaType.EBOOK)
    file_format: str = Field(min_length=1, max_length=32)
    storage_path: str = Field(min_length=1, max_length=1024)
    file_size_bytes: int | None = None
    checksum_sha256: str | None = Field(default=None, max_length=64)

    @field_validator("file_format")
    @classmethod
    def normalize_file_format(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("storage_path")
    @classmethod
    def normalize_storage_path(cls, value: str) -> str:
        return value.strip()


class EbookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author_name: str = Field(min_length=1, max_length=255)
    publisher_name: str | None = Field(default=None, max_length=255)
    genre_names: list[str] = Field(default_factory=list)
    description: str | None = None
    publishing_year: int | None = Field(default=None, ge=0, le=3000)
    series_name: str | None = Field(default=None, max_length=255)
    series_position: int | None = Field(default=None, ge=0)
    has_adaptation: bool = False
    cover_art_path: str | None = Field(default=None, max_length=512)
    isbn_13: str | None = Field(default=None, min_length=10, max_length=13)
    language_code: str | None = Field(default=None, max_length=8)
    files: list[EbookFileCreate] = Field(default_factory=list)

    @field_validator("title", "author_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("publisher_name", "series_name", "cover_art_path", "isbn_13", "language_code")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("genre_names")
    @classmethod
    def normalize_genre_names(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for genre in value:
            cleaned = genre.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                result.append(cleaned)
        return result

    @model_validator(mode="after")
    def validate_files(self) -> "EbookCreate":
        if not self.files:
            raise ValueError("At least one ebook file is required")
        return self


class EbookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author_name: str | None = Field(default=None, min_length=1, max_length=255)
    publisher_name: str | None = Field(default=None, max_length=255)
    genre_names: list[str] | None = None
    description: str | None = None
    publishing_year: int | None = Field(default=None, ge=0, le=3000)
    series_name: str | None = Field(default=None, max_length=255)
    series_position: int | None = Field(default=None, ge=0)
    has_adaptation: bool | None = None
    cover_art_path: str | None = Field(default=None, max_length=512)
    isbn_13: str | None = Field(default=None, min_length=10, max_length=13)
    language_code: str | None = Field(default=None, max_length=8)
    replace_file: EbookFileCreate | None = None

    @field_validator("title", "author_name")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("publisher_name", "series_name", "cover_art_path", "isbn_13", "language_code")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("genre_names")
    @classmethod
    def normalize_genre_names(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        seen: set[str] = set()
        result: list[str] = []
        for genre in value:
            cleaned = genre.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                result.append(cleaned)
        return result


class EbookFileRead(BaseModel):
    id: int
    media_type: MediaType
    file_format: str
    storage_path: str
    file_size_bytes: int | None = None
    checksum_sha256: str | None = None


class EbookRead(BaseModel):
    id: int
    owner_username: str
    title: str
    author_name: str
    publisher_name: str | None = None
    genre_names: list[str] = Field(default_factory=list)
    description: str | None = None
    publishing_year: int | None = None
    series_name: str | None = None
    series_position: int | None = None
    has_adaptation: bool
    cover_art_path: str | None = None
    isbn_13: str | None = None
    language_code: str | None = None
    files: list[EbookFileRead] = Field(default_factory=list)


class EbookListResponse(BaseModel):
    items: list[EbookRead] = Field(default_factory=list)
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool
