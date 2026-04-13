from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.models import entities  # noqa: F401
from app.db.session import engine


def _ensure_user_auth_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(users)"))
        columns = {row[1] for row in rows}

        if "password_salt" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_salt VARCHAR(64) NOT NULL DEFAULT ''"))

        if "password_hash" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(128) NOT NULL DEFAULT ''"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_user_auth_columns()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
