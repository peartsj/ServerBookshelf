from fastapi import Header, HTTPException, status

from app.core.auth import decode_access_token


def resolve_active_username(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token required")

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization must use Bearer token",
        )

    try:
        return decode_access_token(credentials.strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
