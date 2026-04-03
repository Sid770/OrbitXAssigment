"""Application configuration management."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration class."""

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Application
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")

    # Paths
    BASE_DIR: Path = Path(__file__).parent.absolute()
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))

    # Processing
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    SUPPORTED_FORMATS: list[str] = os.getenv("SUPPORTED_FORMATS", "pdf,txt").split(",")

    def __post_init__(self) -> None:
        """Validate configuration on initialization."""
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        return True


# Create config instance
config = Config()
