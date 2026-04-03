"""Text extraction from documents."""
from pathlib import Path
import pdfplumber
from src.utils.logging import get_logger
from src.utils.errors import ExtractionError, CorruptedFileError, EmptyFileError

logger = get_logger(__name__)


class TextExtractor:
    """Handles text extraction from PDF and TXT files."""

    def extract(self, file_path: str) -> str:
        """
        Extract text from a file.

        Args:
            file_path: Path to file

        Returns:
            Extracted text content

        Raises:
            ExtractionError: If extraction fails
        """
        path = Path(file_path)

        try:
            if path.suffix.lower() == ".pdf":
                return self._extract_pdf(path)
            elif path.suffix.lower() == ".txt":
                return self._extract_txt(path)
            else:
                raise ExtractionError(f"Unsupported file type: {path.suffix}")
        except ExtractionError:
            raise
        except Exception as e:
            logger.error("extraction_error", file=path.name, error=str(e))
            raise ExtractionError(f"Failed to extract text from {path.name}: {str(e)}")

    def _extract_pdf(self, file_path: Path) -> str:
        """
        Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text

        Raises:
            CorruptedFileError: If PDF is corrupted
            EmptyFileError: If PDF has no readable text
        """
        try:
            text_parts = []

            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) == 0:
                    raise EmptyFileError("PDF has no pages")

                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as e:
                        logger.warning(
                            "pdf_page_extraction_failed",
                            file=file_path.name,
                            page=page_num,
                            error=str(e),
                        )
                        continue

            if not text_parts:
                raise EmptyFileError("No readable text found in PDF")

            text = "\n".join(text_parts)
            logger.debug("pdf_extracted", file=file_path.name, chars=len(text))
            return text

        except pdfplumber.PDFException as e:
            logger.error("pdf_corrupted", file=file_path.name, error=str(e))
            raise CorruptedFileError(f"PDF file is corrupted: {str(e)}")
        except (EmptyFileError, ExtractionError):
            raise
        except Exception as e:
            raise CorruptedFileError(f"Failed to read PDF: {str(e)}")

    def _extract_txt(self, file_path: Path) -> str:
        """
        Extract text from TXT file.

        Args:
            file_path: Path to TXT file

        Returns:
            File content

        Raises:
            ExtractionError: If file cannot be read
            EmptyFileError: If file is empty
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            if not text.strip():
                raise EmptyFileError("Text file is empty")

            logger.debug("txt_extracted", file=file_path.name, chars=len(text))
            return text

        except UnicodeDecodeError as e:
            logger.error("txt_encoding_error", file=file_path.name, error=str(e))
            try:
                # Fallback to latin-1 encoding
                with open(file_path, "r", encoding="latin-1") as f:
                    text = f.read()
                if not text.strip():
                    raise EmptyFileError("Text file is empty")
                logger.debug("txt_extracted_fallback", file=file_path.name)
                return text
            except Exception as e2:
                raise ExtractionError(f"Cannot decode text file: {str(e2)}")
        except EmptyFileError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to read text file: {str(e)}")
