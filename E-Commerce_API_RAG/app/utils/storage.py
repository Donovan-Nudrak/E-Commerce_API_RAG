import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


async def upload_image(file: UploadFile) -> str | None:
    try:
        if not file.filename or "." not in file.filename:
            return None

        extension = file.filename.rsplit(".", 1)[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            logger.error("Unsupported image extension: %s", extension)
            return None

        upload_dir = Path(settings.UPLOAD_DIR) / "products"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{uuid.uuid4()}.{extension}"
        destination = upload_dir / file_name
        destination.write_bytes(await file.read())

        prefix = settings.MEDIA_URL_PREFIX.rstrip("/")
        return f"{prefix}/products/{file_name}"

    except OSError as error:
        logger.error("Failed to upload image: %s", error)
        return None
