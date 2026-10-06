import hashlib
import os
import uuid
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from fastapi import UploadFile

from backend.app.core.exceptions import (
    InvalidRequestError,
    UnsupportedMediaTypeError,
    FileTooLargeError
)

# Magic byte signatures for supported file types
MAGIC_SIGNATURES: Dict[str, bytes] = {
    "application/pdf": b"%PDF",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}

# Extension to expected MIME mapping
EXTENSION_MIME_MAP: Dict[str, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def detect_mime_by_magic_bytes(header_bytes: bytes) -> Optional[str]:
    """Inspects leading bytes (magic numbers) to determine the real MIME type."""
    if header_bytes.startswith(MAGIC_SIGNATURES["application/pdf"]):
        return "application/pdf"
    if header_bytes.startswith(MAGIC_SIGNATURES["image/png"]):
        return "image/png"
    if header_bytes.startswith(MAGIC_SIGNATURES["image/jpeg"]):
        return "image/jpeg"
    return None


def extract_file_extension(filename: Optional[str]) -> str:
    """Extracts and normalizes the file extension without the leading dot."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].strip().lower()


class DocumentStorageService:
    """Handles file validation, magic-byte inspection, SHA-256 hashing, and local disk storage."""

    def __init__(
        self,
        storage_dir: str = "storage/invoices",
        max_file_size: int = 10 * 1024 * 1024,
        allowed_extensions: Optional[Set[str]] = None,
    ):
        self.storage_dir = Path(storage_dir)
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or {"pdf", "png", "jpg", "jpeg"}

    def ensure_storage_dir(self) -> Path:
        """Creates the storage directory if it does not exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        return self.storage_dir

    async def validate_and_store(
        self, file: UploadFile
    ) -> Tuple[uuid.UUID, str, str, int, str, str]:
        """
        Validates the uploaded file stream and stores it safely.
        
        Returns:
            Tuple of:
            - invoice_id (UUID)
            - relative_storage_path (str)
            - file_hash (SHA-256 str)
            - file_size_bytes (int)
            - verified_mime_type (str)
            - safe_filename (str)
            
        Raises:
            AppException subclasses with appropriate 400, 413, or 415 status codes.
        """
        if not file.filename:
            raise InvalidRequestError(message="Uploaded file must have a valid filename.")

        # Sanitize filename to prevent path traversal vectors in the DB string
        safe_filename = os.path.basename(file.filename.replace("\\", "/"))

        ext = extract_file_extension(safe_filename)
        if ext not in self.allowed_extensions:
            raise UnsupportedMediaTypeError(
                message=f"File extension '.{ext}' is unsupported. "
                        f"Allowed extensions: {', '.join(sorted(self.allowed_extensions))}"
            )

        expected_mime = EXTENSION_MIME_MAP.get(ext)
        
        if file.content_type and file.content_type != expected_mime:
             raise UnsupportedMediaTypeError(
                message=f"Content-Type mismatch. The file extension is '.{ext}' ({expected_mime}), "
                        f"but the provided Content-Type is '{file.content_type}'."
            )

        # Generate a secure internal UUID and target storage path
        invoice_uuid = uuid.uuid4()
        storage_folder = self.ensure_storage_dir()
        target_filename = f"{invoice_uuid}.{ext}"
        target_path = storage_folder / target_filename
        temp_path = storage_folder / f"{target_filename}.tmp"

        sha256_hasher = hashlib.sha256()
        total_bytes = 0
        header_checked = False
        detected_mime: Optional[str] = None

        CHUNK_SIZE = 64 * 1024  # 64 KB chunks

        try:
            with open(temp_path, "wb") as f_out:
                while True:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    # 1. Verify magic bytes on the first chunk
                    if not header_checked:
                        detected_mime = detect_mime_by_magic_bytes(chunk)
                        if not detected_mime:
                            raise UnsupportedMediaTypeError(
                                message="Invalid file content signature. The file content does "
                                        "not match any supported document format (PDF, PNG, JPEG)."
                            )
                        if detected_mime != expected_mime:
                            raise UnsupportedMediaTypeError(
                                message=f"File signature mismatch. The file extension is '.{ext}', "
                                        f"but the actual content signature is '{detected_mime}'."
                            )
                        header_checked = True

                    total_bytes += len(chunk)

                    # 2. Enforce 10 MB maximum size limit
                    if total_bytes > self.max_file_size:
                        raise FileTooLargeError(
                            message=f"File size exceeds the {self.max_file_size // (1024 * 1024)} MB limit. "
                                    f"Uploaded size: {total_bytes} bytes."
                        )

                    sha256_hasher.update(chunk)
                    f_out.write(chunk)

            # Ensure file is not empty
            if total_bytes == 0:
                raise InvalidRequestError(message="Uploaded file is empty (0 bytes).")

            # Atomically rename temp file to permanent file
            temp_path.replace(target_path)

        except Exception:
            # Clean up temporary file if validation failed or an error occurred
            if temp_path.exists():
                temp_path.unlink()
            raise

        file_hash = sha256_hasher.hexdigest()
        relative_path = str(Path(self.storage_dir.name) / target_filename).replace("\\", "/")

        return invoice_uuid, relative_path, file_hash, total_bytes, detected_mime, safe_filename
