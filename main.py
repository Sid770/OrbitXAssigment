"""FastAPI application for document processing pipeline."""
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import shutil
import json
from datetime import datetime

from config import config
from src.utils.logging import setup_logging, get_logger
from src.pipeline import PipelineOrchestrator
from src.utils.errors import DocumentPipelineError

# Setup logging
setup_logging(log_level=config.LOG_LEVEL)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Document Processing Pipeline",
    description="AI-powered document processing with Gemini",
    version="1.0.0",
)

# Add CORS middleware - Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processor
try:
    processor = PipelineOrchestrator(
        gemini_api_key=config.GEMINI_API_KEY,
        output_dir=str(config.OUTPUT_DIR),
    )
except Exception as e:
    logger.error("processor_initialization_failed", error=str(e))
    raise


# Request/Response Models
class ProcessingRequest(BaseModel):
    """Request model for batch processing."""

    folder_path: str
    skip_extraction: bool = False


class ProcessingResponse(BaseModel):
    """Response model for processing results."""

    status: str
    statistics: dict
    output_file: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    environment: str
    api_key_configured: bool


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check application health and configuration."""
    return HealthResponse(
        status="healthy",
        environment=config.APP_ENV,
        api_key_configured=bool(config.GEMINI_API_KEY),
    )


@app.post("/process-folder", response_model=ProcessingResponse)
async def process_folder(request: ProcessingRequest):
    """
    Process all documents in a folder.

    Args:
        request: Processing request with folder path

    Returns:
        Processing results and statistics
    """
    try:
        logger.info("processing_request_received", folder=request.folder_path)

        # Validate folder exists
        folder = Path(request.folder_path)
        if not folder.exists() or not folder.is_dir():
            raise HTTPException(status_code=400, detail="Invalid folder path")

        # Process documents
        final_report, statistics = processor.process_folder(request.folder_path)

        return ProcessingResponse(
            status="completed",
            statistics={
                "total_files": statistics.total_files,
                "processed": statistics.processed,
                "successful": statistics.successful,
                "failed": statistics.failed,
                "skipped": statistics.skipped,
            },
            output_file=str(statistics.end_time)
        )

    except DocumentPipelineError as e:
        logger.error("processing_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/upload-and-process")
async def upload_and_process(
    files: list[UploadFile] = File(...),
    skip_extraction: bool = False,
):
    """
    Upload documents and process them.

    Args:
        files: List of files to process
        skip_extraction: Skip LLM extraction if True

    Returns:
        Processing results
    """
    upload_dir = config.UPLOAD_DIR / "temp"
    upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("file_upload_started", file_count=len(files))

        # Validate and save files
        for file in files:
            # Validate file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in [".pdf", ".txt"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file_ext}",
                )

            # Save file
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            logger.debug("file_saved", filename=file.filename)

        # Process folder
        final_report, statistics = processor.process_folder(str(upload_dir))

        # Cleanup
        shutil.rmtree(upload_dir, ignore_errors=True)

        # Transform documents to frontend format and save individually
        documents = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for doc in final_report.get("documents", []):
            doc_data = {
                "file": doc.get("file", "unknown"),
                "doc_type": doc.get("doc_type", "unknown"),
                "extracted_fields": doc.get("extracted_fields", {}),
                "summary": doc.get("summary", ""),
                "confidence": doc.get("confidence", "low"),
                "errors": doc.get("errors", []),
                "text_length": doc.get("text_length", 0),
                "processing_time_seconds": doc.get("processing_time_seconds", 0),
            }
            documents.append(doc_data)

            # Save individual document to JSON file
            filename_without_ext = Path(doc.get("file", "unknown")).stem
            output_filename = f"document_{filename_without_ext}_{timestamp}.json"
            output_path = config.OUTPUT_DIR / output_filename

            with open(output_path, 'w') as f:
                json.dump(doc_data, f, indent=2)

            logger.info("document_saved", filename=output_filename, path=str(output_path))

        # Return results in frontend-compatible format
        return {
            "documents": documents,
            "pipeline_report": {
                "timestamp": final_report.get("timestamp"),
                "summary": final_report.get("summary"),
                "statistics": final_report.get("statistics", {
                    "total_files": statistics.total_files,
                    "processed": statistics.processed,
                    "successful": statistics.successful,
                    "failed": statistics.failed,
                    "skipped": statistics.skipped,
                })
            }
        }

    except DocumentPipelineError as e:
        logger.error("processing_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("upload_processing_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/results/{filename}")
async def get_result_file(filename: str):
    """
    Download a result file.

    Args:
        filename: Name of result file

    Returns:
        File content
    """
    try:
        file_path = config.OUTPUT_DIR / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        logger.info("result_file_downloaded", filename=filename)
        return FileResponse(
            file_path,
            media_type="application/json",
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("file_download_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/results")
async def list_results():
    """List all available result files."""
    try:
        files = [f.name for f in config.OUTPUT_DIR.glob("*.json")]
        logger.info("results_listed", file_count=len(files))
        return {
            "files": files,
            "output_directory": str(config.OUTPUT_DIR),
        }
    except Exception as e:
        logger.error("list_results_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api")
async def api_root():
    """API documentation."""
    return {
        "message": "Document Processing Pipeline API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "process_folder": "POST /process-folder",
            "upload_and_process": "POST /upload-and-process",
            "list_results": "GET /results",
            "get_result": "GET /results/{filename}",
        },
    }


# Mount static files with /static prefix
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Serve index.html for root and SPA routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend application."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return """
    <html>
        <body>
            <h1>Document Processing Pipeline</h1>
            <p>Static files not found. Make sure the static/ directory exists.</p>
        </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
    )
