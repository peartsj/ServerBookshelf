from pydantic import BaseModel, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Category name cannot be empty")
        return cleaned


class CategoryRead(BaseModel):
    id: int
    name: str
