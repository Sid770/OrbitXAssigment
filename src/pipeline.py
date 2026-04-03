"""
Modular AI Document Processing Pipeline Orchestration.

Implements a 10-step document processing pipeline with robust error handling,
logging at each step, and comprehensive statistics.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Generator, Optional, Tuple
from dataclasses import dataclass, field, asdict

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

# Confidence threshold for document classification
CONFIDENCE_THRESHOLD = 0.7


@dataclass
class DocumentResult:
    """Output format for a single processed document."""

    file: str
    doc_type: str = "unknown"
    extracted_fields: dict = field(default_factory=dict)
    summary: str = ""
    confidence: str = "low"
    errors: list = field(default_factory=list)
    text_length: int = 0
    processing_time_seconds: float = 0.0


@dataclass
class PipelineStatistics:
    """Statistics for pipeline execution."""

    total_files: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def get_summary_report(self) -> str:
        """Generate human-readable summary report."""
        return (
            f"Processed {self.processed}/{self.total_files} files, "
            f"{self.failed} failed, {self.skipped} skipped"
        )


class PipelineOrchestrator:
    """
    Orchestrates the 10-step document processing pipeline.

    Pipeline steps:
    1. Load file from folder
    2. Extract text
    3. If empty → mark as skipped
    4. Call document classification prompt
    5. If confidence is low → set doc_type = "unknown"
    6. Based on doc_type → call extraction prompt
    7. Parse JSON safely
    8. If JSON parsing fails → retry once
    9. Generate summary using LLM
    10. Capture errors (do NOT crash)
    """

    def __init__(
        self,
        gemini_api_key: str,
        output_dir: str = "./outputs",
        max_file_size_mb: int = 50,
    ):
        """
        Initialize pipeline orchestrator.

        Args:
            gemini_api_key: Google Gemini API key
            output_dir: Directory for output files
            max_file_size_mb: Maximum file size in MB
        """
        logger.info("initializing_pipeline_orchestrator")

        self.ingester = DocumentIngester(max_file_size_mb=max_file_size_mb)
        self.extractor = TextExtractor()
        self.llm = GeminiClient(gemini_api_key)
        self.output_writer = OutputWriter(output_dir)
        self.output_dir = Path(output_dir)

    def process_folder(self, folder_path: str) -> Tuple[dict, PipelineStatistics]:
        """
        Process all documents in a folder through the complete pipeline.

        Args:
            folder_path: Path to folder containing documents

        Returns:
            Tuple of (final_report dict, statistics)
        """
        logger.info("pipeline_started", folder=folder_path)

        stats = PipelineStatistics(start_time=datetime.now())
        results = []

        try:
            # Step 1: Load files from folder (via ingester)
            logger.info("step_1_loading_files", folder=folder_path)
            files_to_process = list(self.ingester.ingest_folder(folder_path))
            stats.total_files = len(files_to_process)

            for doc_metadata in files_to_process:
                try:
                    result = self._process_single_document(doc_metadata)
                    results.append(asdict(result))

                    if result.errors:
                        stats.failed += 1
                        stats.errors.append(
                            {"file": result.file, "errors": result.errors}
                        )
                    else:
                        stats.successful += 1

                    stats.processed += 1

                except Exception as e:
                    # Capture errors - do NOT crash
                    logger.error(
                        "document_processing_exception",
                        file=doc_metadata.get("file_name"),
                        error=str(e),
                    )
                    stats.failed += 1
                    stats.processed += 1
                    stats.errors.append(
                        {"file": doc_metadata.get("file_name"), "error": str(e)}
                    )

        except Exception as e:
            logger.error("folder_processing_failed", error=str(e))
            # Don't raise - continue and report what we have

        stats.end_time = datetime.now()

        # Write results
        logger.info("writing_results", count=len(results))
        self._write_results(results, stats)

        # Generate final report with documents
        final_report = self._generate_final_report(stats, results)

        logger.info("pipeline_completed", summary=stats.get_summary_report())

        return final_report, stats

    def _process_single_document(self, doc_metadata: dict) -> DocumentResult:
        """
        Process a single document through the 10-step pipeline.

        Args:
            doc_metadata: Document metadata from ingester

        Returns:
            DocumentResult with all processing results

        Raises:
            Exception: To be caught by caller for error tracking
        """
        file_name = doc_metadata["file_name"]
        file_path = doc_metadata["file_path"]
        result = DocumentResult(file=file_name)

        step_start = datetime.now()

        try:
            # Step 2: Extract text
            logger.debug("step_2_extracting_text", file=file_name)
            text = self._extract_text(file_path)
            result.text_length = len(text)

            # Step 3: If empty → mark as skipped
            if not text or not text.strip():
                logger.info("step_3_document_empty", file=file_name)
                result.errors.append("Document text is empty - skipped")
                return result

            # Step 4: Call document classification prompt
            logger.debug("step_4_classifying_document", file=file_name)
            classification = self._classify_document(text)

            # Step 5: If confidence is low → set doc_type = "unknown"
            doc_type = self._get_document_type(classification)

            # Convert string confidence to numeric for comparison
            confidence_str = classification.get("confidence", "low").lower()
            confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.3}
            confidence_numeric = confidence_map.get(confidence_str, 0.3)

            confidence_level = "low"
            if confidence_numeric >= CONFIDENCE_THRESHOLD:
                confidence_level = "high"
            result.confidence = confidence_level

            result.doc_type = doc_type
            logger.debug(
                "step_5_confidence_check",
                file=file_name,
                doc_type=doc_type,
                confidence=confidence_level,
            )

            # Step 6: Based on doc_type → call extraction prompt
            logger.debug("step_6_extracting_fields", file=file_name, doc_type=doc_type)
            extracted = self._extract_fields(text, doc_type)
            result.extracted_fields = extracted

            # Step 7 & 8: Parse JSON safely with retry
            logger.debug("step_7_8_json_parsing", file=file_name)
            if not isinstance(extracted, dict):
                result.errors.append("Extraction result is not a dictionary")

            # Step 9: Generate summary using LLM
            logger.debug("step_9_generating_summary", file=file_name)
            summary = self._generate_summary(text, doc_type)
            result.summary = summary.get("summary", "")

        except ExtractionError as e:
            result.errors.append(f"Text extraction failed: {str(e)}")
            logger.error(
                "step_2_extraction_error",
                file=file_name,
                error=str(e),
            )
        except LLMError as e:
            result.errors.append(f"LLM processing failed: {str(e)}")
            logger.error("llm_error", file=file_name, error=str(e))
        except Exception as e:
            # Step 10: Capture errors (do NOT crash)
            result.errors.append(f"Unexpected error: {str(e)}")
            logger.error(
                "step_10_unexpected_error",
                file=file_name,
                error=str(e),
            )

        # Calculate processing time
        result.processing_time_seconds = (
            datetime.now() - step_start
        ).total_seconds()

        logger.info(
            "document_processing_complete",
            file=file_name,
            doc_type=result.doc_type,
            errors=len(result.errors),
            time_seconds=result.processing_time_seconds,
        )

        return result

    def _extract_text(self, file_path: str) -> str:
        """
        Step 2: Extract text from file.

        Args:
            file_path: Path to file

        Returns:
            Extracted text content

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            text = self.extractor.extract(file_path)
            logger.debug("text_extracted", file_path=file_path, chars=len(text))
            return text
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to extract text: {str(e)}")

    def _classify_document(self, text: str) -> dict:
        """
        Step 4: Classify document using LLM.

        Args:
            text: Document text content

        Returns:
            Classification result with doc_type, confidence, reasoning

        Raises:
            LLMError: If classification fails
        """
        try:
            classification = self.llm.classify_document(text)
            logger.debug(
                "document_classified",
                doc_type=classification.get("doc_type"),
                confidence=classification.get("confidence"),
            )
            return classification
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Classification failed: {str(e)}")

    def _get_document_type(self, classification: dict) -> str:
        """
        Step 5: Determine document type with confidence check.

        If confidence is below threshold, mark as "unknown".

        Args:
            classification: Classification result

        Returns:
            Document type string
        """
        # Convert string confidence to numeric
        confidence_str = classification.get("confidence", "low")
        if isinstance(confidence_str, str):
            confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.3}
            confidence = confidence_map.get(confidence_str.lower(), 0.3)
        else:
            confidence = float(confidence_str) if confidence_str else 0.3

        if confidence < CONFIDENCE_THRESHOLD:
            logger.debug("low_confidence_document", confidence=confidence)
            return "unknown"

        doc_type = classification.get("doc_type", "unknown")
        return doc_type if doc_type else "unknown"

    def _extract_fields(self, text: str, doc_type: str) -> dict:
        """
        Step 6: Extract fields based on document type.

        Includes steps 7-8: JSON parsing with retry logic.

        Args:
            text: Document text content
            doc_type: Document type

        Returns:
            Extracted fields as dictionary

        Raises:
            LLMError: If extraction fails after retries
        """
        max_retries = 2  # Initial attempt + 1 retry

        for attempt in range(max_retries):
            try:
                logger.debug(
                    "extracting_fields",
                    doc_type=doc_type,
                    attempt=attempt + 1,
                )
                extraction = self.llm.extract_information(text, doc_type)

                # Validate result is dictionary
                if not isinstance(extraction, dict):
                    raise LLMError("Extraction result is not a dictionary")

                logger.debug("fields_extracted", doc_type=doc_type)
                return extraction

            except LLMError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        "extraction_retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                    )
                    continue
                else:
                    logger.error(
                        "extraction_failed_max_retries",
                        max_retries=max_retries,
                        error=str(e),
                    )
                    raise LLMError(f"Extraction failed after {max_retries} attempts")

        return {}

    def _generate_summary(self, text: str, doc_type: str) -> dict:
        """
        Step 9: Generate summary using LLM.

        Args:
            text: Document text content
            doc_type: Document type

        Returns:
            Dictionary with summary field

        Raises:
            LLMError: If summarization fails
        """
        try:
            logger.debug("generating_summary", doc_type=doc_type)
            summary = self.llm.summarize_document(text, doc_type)
            logger.debug("summary_generated", doc_type=doc_type)
            return summary
        except LLMError:
            # Don't fail the pipeline if summary generation fails
            logger.warning("summary_generation_failed", doc_type=doc_type)
            return {"summary": "Summary could not be generated"}
        except Exception as e:
            logger.warning("summary_generation_error", error=str(e))
            return {"summary": "Summary could not be generated"}

    def _write_results(self, results: list, stats: PipelineStatistics) -> None:
        """
        Write processing results to output file.

        Args:
            results: List of DocumentResult dictionaries
            stats: Pipeline statistics
        """
        try:
            output_data = {
                "pipeline_report": {
                    "timestamp": datetime.now().isoformat(),
                    "summary": stats.get_summary_report(),
                    "statistics": {
                        "total_files": stats.total_files,
                        "processed": stats.processed,
                        "successful": stats.successful,
                        "failed": stats.failed,
                        "skipped": stats.skipped,
                        "elapsed_seconds": stats.elapsed_seconds,
                    },
                },
                "documents": results,
            }

            # Write JSON report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pipeline_results_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info("results_written", file=filename, documents=len(results))

        except Exception as e:
            logger.error("results_writing_failed", error=str(e))

    def _generate_final_report(self, stats: PipelineStatistics, documents: list = None) -> dict:
        """
        Generate final summary report.

        Args:
            stats: Pipeline statistics
            documents: List of processed documents

        Returns:
            Final report dictionary
        """
        if documents is None:
            documents = []

        return {
            "status": "completed",
            "summary": stats.get_summary_report(),
            "timestamp": datetime.now().isoformat(),
            "documents": documents,
            "statistics": {
                "total_files": stats.total_files,
                "processed": stats.processed,
                "successful": stats.successful,
                "failed": stats.failed,
                "skipped": stats.skipped,
                "elapsed_seconds": stats.elapsed_seconds,
            },
            "errors": stats.errors if stats.errors else [],
        }
