from pydantic import BaseModel


class UploadResponse(BaseModel):
    original_filename: str
    stored_filename: str
    storage_path: str
    file_format: str
    size_bytes: int
    checksum_sha256: str
    owner_username: str
