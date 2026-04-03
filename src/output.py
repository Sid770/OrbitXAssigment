"""Output writing and result serialization."""
import json
from pathlib import Path
from datetime import datetime
from src.utils.logging import get_logger
from src.utils.errors import OutputError

logger = get_logger(__name__)


class OutputWriter:
    """Handles writing processing results to files."""

    def __init__(self, output_dir: str = "./outputs"):
        """
        Initialize output writer.

        Args:
            output_dir: Directory to write output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("output_writer_initialized", output_dir=str(self.output_dir))

    def write_results(self, results: list[dict]) -> Path:
        """
        Write processing results to JSON file.

        Args:
            results: List of processing results

        Returns:
            Path to written file

        Raises:
            OutputError: If writing fails
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results_{timestamp}.json"
            filepath = self.output_dir / filename

            output = {
                "timestamp": datetime.now().isoformat(),
                "total_documents": len(results),
                "successful_documents": sum(1 for r in results if r["success"]),
                "results": results,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            logger.info("results_written", file=filename, documents=len(results))
            return filepath

        except Exception as e:
            logger.error("output_writing_failed", error=str(e))
            raise OutputError(f"Failed to write results: {str(e)}")

    def write_document_report(
        self, doc_name: str, analysis: dict, format: str = "json"
    ) -> Path:
        """
        Write individual document analysis report.

        Args:
            doc_name: Document name
            analysis: Analysis data
            format: Output format (json)

        Returns:
            Path to written file

        Raises:
            OutputError: If writing fails
        """
        try:
            safe_name = "".join(c for c in doc_name if c.isalnum() or c in "._- ")
            safe_name = safe_name.rsplit(".", 1)[0]  # Remove original extension

            filepath = self.output_dir / f"{safe_name}_analysis.json"

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)

            logger.info("document_report_written", file=filepath.name)
            return filepath

        except Exception as e:
            logger.error("document_report_writing_failed", error=str(e))
            raise OutputError(f"Failed to write document report: {str(e)}")

    def write_summary(self, summary: dict) -> Path:
        """
        Write processing summary.

        Args:
            summary: Summary data

        Returns:
            Path to written file

        Raises:
            OutputError: If writing fails
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.info("summary_written", file=filename)
            return filepath

        except Exception as e:
            logger.error("summary_writing_failed", error=str(e))
            raise OutputError(f"Failed to write summary: {str(e)}")
