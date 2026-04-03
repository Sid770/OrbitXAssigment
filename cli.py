"""Command-line interface for document processing."""
import sys
import argparse
from pathlib import Path

from config import config
from src.utils.logging import setup_logging, get_logger
from src.processing import DocumentProcessor
from src.utils.errors import DocumentPipelineError

logger = get_logger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Document Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --folder ./documents
  python cli.py --folder ./docs --skip-extraction
  python cli.py --folder ./data --log-level DEBUG
        """,
    )

    parser.add_argument(
        "--folder",
        "-f",
        required=True,
        help="Path to folder containing documents",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip LLM extraction (text extraction only)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(config.OUTPUT_DIR),
        help="Output directory for results",
    )
    parser.add_argument(
        "--log-level",
        default=config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_level=args.log_level)

    # Validate arguments
    folder = Path(args.folder)
    if not folder.exists():
        logger.error("folder_not_found", path=str(folder))
        sys.exit(1)

    if not folder.is_dir():
        logger.error("path_not_directory", path=str(folder))
        sys.exit(1)

    try:
        # Initialize processor
        logger.info("initialization_started")
        processor = DocumentProcessor(
            gemini_api_key=config.GEMINI_API_KEY,
            output_dir=args.output_dir,
        )

        # Process documents
        logger.info("processing_started", folder=str(folder))
        result = processor.process_folder(
            str(folder),
            skip_extraction=args.skip_extraction,
        )

        # Print summary
        print("\n" + "=" * 60)
        print("PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Successful: {result['statistics']['successful']}")
        print(f"Failed: {result['statistics']['failed']}")
        print(f"Total: {result['statistics']['total_processed']}")
        print(f"Time: {result['statistics']['processing_time_seconds']:.2f}s")
        print(f"Output: {result['output_file']}")
        print("=" * 60 + "\n")

    except DocumentPipelineError as e:
        logger.error("pipeline_error", error=str(e))
        print(f"\nError: {str(e)}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        print(f"\nUnexpected error: {str(e)}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
