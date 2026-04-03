"""Custom exception classes."""


class DocumentPipelineError(Exception):
    """Base exception for document pipeline errors."""

    pass


class IngestionError(DocumentPipelineError):
    """Raised when file ingestion fails."""

    pass


class ExtractionError(DocumentPipelineError):
    """Raised when text extraction fails."""

    pass


class UnsupportedFileTypeError(IngestionError):
    """Raised when file type is not supported."""

    pass


class CorruptedFileError(ExtractionError):
    """Raised when file is corrupted."""

    pass


class EmptyFileError(ExtractionError):
    """Raised when file is empty."""

    pass


class LLMError(DocumentPipelineError):
    """Raised when LLM processing fails."""

    pass


class ProcessingError(DocumentPipelineError):
    """Raised during document processing."""

    pass


class OutputError(DocumentPipelineError):
    """Raised during output writing."""

    pass
