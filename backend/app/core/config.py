from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bookshelf Service"
    app_env: str = "development"
    database_url: str = "sqlite:///./data/library.db"
    upload_root: str = "./uploads"
    max_upload_size_mb: int = 25
    cors_allow_origins: str = "http://localhost:4409,http://127.0.0.1:4409"
    auth_secret: str = "bookshelf-dev-secret-change-me"
    auth_token_ttl_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]
        return origins if origins else ["*"]


settings = Settings()
