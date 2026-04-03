"""
Updated Document Processing with Pipeline Orchestrator Integration.

This module shows how to integrate the new PipelineOrchestrator
with the existing FastAPI application and DocumentProcessor class.
"""

from pathlib import Path
from datetime import datetime
from src.ingestion import DocumentIngester
from src.extraction import TextExtractor
from src.llm import GeminiClient
from src.output import OutputWriter
from src.pipeline import PipelineOrchestrator
from src.utils.logging import get_logger
from src.utils.errors import DocumentPipelineError

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Enhanced document processor with pipeline orchestration.

    Provides both legacy interface (process_folder) and new orchestrator
    for backward compatibility.
    """

    def __init__(self, gemini_api_key: str, output_dir: str = "./outputs"):
        """
        Initialize document processor.

        Args:
            gemini_api_key: Google Gemini API key
            output_dir: Directory for output files
        """
        self.orchestrator = PipelineOrchestrator(
            gemini_api_key=gemini_api_key,
            output_dir=output_dir,
        )
        self.output_writer = OutputWriter(output_dir)
        logger.info("document_processor_initialized")

    def process_folder(
        self, folder_path: str, skip_extraction: bool = False
    ) -> dict:
        """
        Process all documents in a folder through the pipeline.

        Legacy interface for backward compatibility with FastAPI routes.

        Args:
            folder_path: Path to folder containing documents
            skip_extraction: Skip LLM extraction if True (legacy parameter)

        Returns:
            Processing summary with results and statistics

        Raises:
            DocumentPipelineError: If processing fails critically
        """
        logger.info("processing_started", folder=folder_path, skip_extraction=skip_extraction)

        try:
            # Use the new orchestrator
            final_report, stats = self.orchestrator.process_folder(folder_path)

            # Convert to legacy format for backward compatibility
            return {
                "status": final_report["status"],
                "statistics": final_report["statistics"],
                "output_file": str(self.orchestrator.output_dir / f"pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"),
            }

        except Exception as e:
            logger.error("pipeline_processing_failed", error=str(e))
            raise DocumentPipelineError(f"Pipeline processing failed: {str(e)}")


# ============================================================================
# USAGE INTEGRATION EXAMPLES
# ============================================================================


def example_1_fastapi_integration():
    """
    Example: Using PipelineOrchestrator in FastAPI routes.

    This shows how to integrate into the existing main.py FastAPI app.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from config import config

    app = FastAPI()

    try:
        orchestrator = PipelineOrchestrator(
            gemini_api_key=config.GEMINI_API_KEY,
            output_dir=str(config.OUTPUT_DIR),
        )
    except Exception as e:
        logger.error("orchestrator_initialization_failed", error=str(e))
        raise

    class ProcessingRequest(BaseModel):
        folder_path: str

    @app.post("/process-folder-v2")
    async def process_folder_v2(request: ProcessingRequest):
        """NEW: Process folder with enhanced orchestrator."""
        try:
            logger.info("processing_request_received", folder=request.folder_path)

            folder = Path(request.folder_path)
            if not folder.exists() or not folder.is_dir():
                raise HTTPException(status_code=400, detail="Invalid folder path")

            final_report, stats = orchestrator.process_folder(request.folder_path)

            logger.info(
                "processing_completed",
                summary=stats.get_summary_report(),
            )

            return {
                "status": final_report["status"],
                "summary": final_report["summary"],
                "statistics": final_report["statistics"],
                "elapsed_seconds": stats.elapsed_seconds,
            }

        except Exception as e:
            logger.error("processing_error", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


def example_2_batch_processing():
    """
    Example: Process multiple folders with error recovery.

    Shows how to process multiple folders while tracking errors.
    """
    from config import config

    orchestrator = PipelineOrchestrator(
        gemini_api_key=config.GEMINI_API_KEY,
        output_dir=str(config.OUTPUT_DIR),
    )

    folders = [
        "./documents",
        "./uploads",
        "./archive",
    ]

    overall_stats = {
        "total_processed": 0,
        "total_successful": 0,
        "total_failed": 0,
        "folders_processed": 0,
        "folders_failed": 0,
    }

    for folder in folders:
        folder_path = Path(folder)

        if not folder_path.exists():
            logger.warning("folder_not_found", path=folder)
            overall_stats["folders_failed"] += 1
            continue

        try:
            logger.info("processing_folder", path=folder)
            final_report, stats = orchestrator.process_folder(folder)

            overall_stats["folders_processed"] += 1
            overall_stats["total_processed"] += stats.processed
            overall_stats["total_successful"] += stats.successful
            overall_stats["total_failed"] += stats.failed

            logger.info(
                "folder_completed",
                folder=folder,
                summary=stats.get_summary_report(),
            )

        except Exception as e:
            logger.error("folder_processing_failed", folder=folder, error=str(e))
            overall_stats["folders_failed"] += 1
            continue

    logger.info("batch_processing_complete", stats=overall_stats)
    return overall_stats


def example_3_error_analysis():
    """
    Example: Analyze errors from processing results.

    Shows how to extract and analyze errors from pipeline results.
    """
    from config import config

    orchestrator = PipelineOrchestrator(
        gemini_api_key=config.GEMINI_API_KEY,
        output_dir=str(config.OUTPUT_DIR),
    )

    final_report, stats = orchestrator.process_folder("./documents")

    # Analyze errors
    if stats.errors:
        logger.warning("processing_had_errors", error_count=len(stats.errors))

        error_types = {}
        for error_entry in stats.errors:
            error_msg = str(error_entry.get("error", "Unknown"))
            error_type = error_msg.split(":")[0]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        logger.info("error_summary", error_types=error_types)

        # Report specific errors
        for error in stats.errors[:5]:  # Report first 5 errors
            logger.warning(
                "error_detail",
                file=error.get("file"),
                error=error.get("error"),
            )

    return {
        "total_errors": len(stats.errors),
        "error_types": error_types if stats.errors else {},
        "success_rate": (stats.successful / stats.processed)
        if stats.processed > 0
        else 0,
    }


if __name__ == "__main__":
    # Demonstrate the processor
    from config import config

    processor = DocumentProcessor(
        gemini_api_key=config.GEMINI_API_KEY,
        output_dir=str(config.OUTPUT_DIR),
    )

    # Test with sample documents
    try:
        result = processor.process_folder("./documents")
        logger.info("processor_test_complete", result=result)
    except Exception as e:
        logger.error("processor_test_failed", error=str(e))
