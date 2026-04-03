"""Document ingestion - file loading and validation."""
from pathlib import Path
from typing import Generator
from src.utils.logging import get_logger
from src.utils.errors import (
    IngestionError,
    UnsupportedFileTypeError,
    EmptyFileError,
)

logger = get_logger(__name__)


class DocumentIngester:
    """Handles document file loading and validation."""

    SUPPORTED_FORMATS = {".pdf", ".txt"}

    def __init__(self, max_file_size_mb: int = 50):
        """
        Initialize ingester.

        Args:
            max_file_size_mb: Maximum file size in megabytes
        """
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def ingest_folder(self, folder_path: str) -> Generator[dict, None, None]:
        """
        Ingest all documents from a folder.

        Args:
            folder_path: Path to folder containing documents

        Yields:
            Dictionary with file metadata and content
        """
        folder = Path(folder_path)

        if not folder.exists():
            logger.error("folder_not_found", path=str(folder))
            raise IngestionError(f"Folder not found: {folder}")

        if not folder.is_dir():
            logger.error("path_not_directory", path=str(folder))
            raise IngestionError(f"Path is not a directory: {folder}")

        total_files = 0
        processed_files = 0
        skipped_files = 0

        for file_path in folder.rglob("*"):
            if file_path.is_file():
                total_files += 1

                try:
                    doc = self._load_file(file_path)
                    if doc:
                        processed_files += 1
                        yield doc
                except (UnsupportedFileTypeError, EmptyFileError) as e:
                    skipped_files += 1
                    logger.warning(
                        "file_skipped",
                        file=file_path.name,
                        reason=str(e),
                    )
                except Exception as e:
                    skipped_files += 1
                    logger.error(
                        "ingestion_error",
                        file=file_path.name,
                        error=str(e),
                    )

        logger.info(
            "ingestion_complete",
            total_files=total_files,
            processed=processed_files,
            skipped=skipped_files,
        )

    def _load_file(self, file_path: Path) -> dict | None:
        """
        Load and validate a single file.

        Args:
            file_path: Path to file to load

        Returns:
            Dictionary with file metadata or None if skipped

        Raises:
            UnsupportedFileTypeError: If file type is not supported
            EmptyFileError: If file is empty
            IngestionError: If file cannot be read
        """
        # Check file extension
        if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise UnsupportedFileTypeError(
                f"Unsupported format: {file_path.suffix}"
            )

        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise EmptyFileError("File is empty")

        if file_size > self.max_file_size_bytes:
            raise IngestionError(
                f"File size ({file_size} bytes) exceeds maximum "
                f"({self.max_file_size_bytes} bytes)"
            )

        try:
            # Read file to check if it's readable
            with open(file_path, "rb") as f:
                _ = f.read(1)  # Read first byte to validate
        except Exception as e:
            raise IngestionError(f"Cannot read file: {str(e)}")

        logger.debug("file_loaded", file=file_path.name, size_bytes=file_size)

        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "file_size": file_size,
        }
