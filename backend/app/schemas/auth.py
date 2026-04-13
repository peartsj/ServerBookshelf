from pydantic import BaseModel, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=4, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Username cannot be empty")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise ValueError("Password must be at least 4 characters")
        return cleaned


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    username: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    password_confirmation: str = Field(min_length=4, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Username cannot be empty")
        return cleaned

    @field_validator("password", "password_confirmation")
    @classmethod
    def validate_password(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise ValueError("Password must be at least 4 characters")
        return cleaned

    @model_validator(mode="after")
    def validate_password_match(self) -> "RegisterRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Password confirmation does not match")
        return self


class MeResponse(BaseModel):
    username: str
