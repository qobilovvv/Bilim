import os
import uuid

import aiofiles
from fastapi import HTTPException, UploadFile, status

async def save_upload_file(
    upload: UploadFile,
    subdir: str,
    allowed_extensions: set[str] | None = None,
    max_size_bytes: int | None = None,
) -> str:
    """Saves an UploadFile under media/<subdir>/ and returns the path relative to media/."""
    ext = upload.filename.rsplit(".", 1)[-1].lower() if upload.filename and "." in upload.filename else ""

    if allowed_extensions is not None and ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '.{ext}'. Allowed: {', '.join(sorted(allowed_extensions))}"
        )

    content = await upload.read()
    if max_size_bytes is not None and len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {max_size_bytes // (1024 * 1024)} MB"
        )

    filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    directory = os.path.join("media", subdir)
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return f"{subdir}/{filename}"

def delete_media_file(relative_path: str | None) -> None:
    if not relative_path:
        return
    full_path = os.path.join("media", relative_path)
    if os.path.exists(full_path):
        os.remove(full_path)
