"""Document processing orchestration."""
from pathlib import Path
from datetime import datetime
from src.ingestion import DocumentIngester
from src.extraction import TextExtractor
from src.llm import GeminiClient
from src.output import OutputWriter
from src.utils.logging import get_logger
from src.utils.errors import (
    DocumentPipelineError,
    IngestionError,
    ExtractionError,
    LLMError,
)

logger = get_logger(__name__)


class DocumentProcessor:
    """Orchestrates the document processing pipeline."""

    def __init__(self, gemini_api_key: str, output_dir: str = "./outputs"):
        """
        Initialize document processor.

        Args:
            gemini_api_key: Google Gemini API key
            output_dir: Directory for output files
        """
        self.ingester = DocumentIngester()
        self.extractor = TextExtractor()
        self.llm = GeminiClient(gemini_api_key)
        self.output_writer = OutputWriter(output_dir)

        logger.info("document_processor_initialized")

    def process_folder(
        self, folder_path: str, skip_extraction: bool = False
    ) -> dict:
        """
        Process all documents in a folder through the pipeline.

        Args:
            folder_path: Path to folder containing documents
            skip_extraction: Skip LLM extraction if True

        Returns:
            Processing summary with results and statistics

        Raises:
            DocumentPipelineError: If processing fails critically
        """
        logger.info("processing_started", folder=folder_path)

        start_time = datetime.now()
        results = []
        stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": [],
        }

        try:
            for ingested_doc in self.ingester.ingest_folder(folder_path):
                result = self._process_single_document(
                    ingested_doc, skip_extraction=skip_extraction
                )

                stats["total_processed"] += 1

                if result["success"]:
                    stats["successful"] += 1
                    results.append(result)
                else:
                    stats["failed"] += 1
                    stats["errors"].append(
                        {
                            "file": result["file_name"],
                            "error": result.get("error"),
                        }
                    )
                    logger.error(
                        "document_processing_failed",
                        file=result["file_name"],
                        error=result.get("error"),
                    )

        except Exception as e:
            logger.error("pipeline_processing_failed", error=str(e))
            raise DocumentPipelineError(f"Pipeline processing failed: {str(e)}")

        # Write results
        output_file = self.output_writer.write_results(results)

        elapsed = (datetime.now() - start_time).total_seconds()
        stats.update(
            {
                "processing_time_seconds": elapsed,
                "output_file": str(output_file),
            }
        )

        logger.info(
            "processing_completed",
            successful=stats["successful"],
            failed=stats["failed"],
            time_seconds=elapsed,
        )

        return {
            "status": "completed",
            "statistics": stats,
            "output_file": str(output_file),
        }

    def _process_single_document(
        self, doc_metadata: dict, skip_extraction: bool = False
    ) -> dict:
        """
        Process a single document through the pipeline.

        Args:
            doc_metadata: Document metadata from ingestion
            skip_extraction: Skip LLM extraction if True

        Returns:
            Result dictionary for this document
        """
        file_name = doc_metadata["file_name"]
        file_path = doc_metadata["file_path"]

        result = {
            "success": False,
            "file_name": file_name,
            "file_path": file_path,
            "file_type": doc_metadata["file_type"],
        }

        try:
            # Extract text
            logger.debug("extracting_text", file=file_name)
            text = self.extractor.extract(file_path)
            result["text_length"] = len(text)

            # Skip LLM if requested
            if skip_extraction:
                result["success"] = True
                result["text_preview"] = text[:500]
                logger.debug("extraction_skipped", file=file_name)
                return result

            # Classify with LLM
            logger.debug("classifying_document", file=file_name)
            classification = self.llm.classify_document(text)
            result["classification"] = classification

            # Extract information
            logger.debug("extracting_information", file=file_name)
            doc_type = classification.get("doc_type", "unknown")
            extraction = self.llm.extract_information(text, doc_type)
            result["extraction"] = extraction

            result["success"] = True
            logger.info("document_processed_successfully", file=file_name)

        except ExtractionError as e:
            result["error"] = f"Extraction failed: {str(e)}"
            logger.error("extraction_error", file=file_name, error=str(e))
        except LLMError as e:
            result["error"] = f"LLM processing failed: {str(e)}"
            logger.error("llm_error", file=file_name, error=str(e))
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error("unexpected_error", file=file_name, error=str(e))

        return result
