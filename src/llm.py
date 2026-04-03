"""Gemini LLM integration for document classification."""
import json
import re
import google.genai
from src.utils.logging import get_logger
from src.utils.errors import LLMError
from src.prompts import (
    get_classification_prompt,
    get_extraction_prompt,
    get_summary_prompt,
    JSON_CONFIG,
)

logger = get_logger(__name__)


class GeminiClient:
    """Handles interaction with Google Gemini API."""

    def __init__(self, api_key: str):
        """
        Initialize Gemini client.

        Args:
            api_key: Google Gemini API key

        Raises:
            LLMError: If API key is invalid
        """
        if not api_key:
            raise LLMError("API key is required")

        try:
            self.client = google.genai.Client(api_key=api_key)
            logger.info("gemini_client_initialized")
        except Exception as e:
            logger.error("gemini_initialization_failed", error=str(e))
            raise LLMError(f"Failed to initialize Gemini: {str(e)}")

    def classify_document(self, text: str, max_retries: int = 3) -> dict:
        """
        Classify document using Gemini with production prompt.

        Args:
            text: Document text content
            max_retries: Number of retries on failure

        Returns:
            Dictionary with doc_type, confidence, reasoning

        Raises:
            LLMError: If classification fails
        """
        if not text or not text.strip():
            raise LLMError("Document text is empty")

        # Truncate text to reasonable length for API
        max_chars = 30000
        text_truncated = text[:max_chars]
        if len(text) > max_chars:
            logger.warning(
                "document_text_truncated",
                original_length=len(text),
                truncated_length=max_chars,
            )

        prompt = get_classification_prompt(text_truncated)

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="models/gemini-3.1-flash-lite-preview",
                    contents=prompt,
                )

                # Debug: log raw response
                logger.debug("raw_response", response_text=response.text[:500])

                result = self._parse_json_response(response.text)

                # Validate response structure
                if "doc_type" not in result:
                    raise LLMError("Missing 'doc_type' in classification response")

                logger.info(
                    "document_classified",
                    doc_type=result.get("doc_type"),
                    confidence=result.get("confidence"),
                )
                return result
            except Exception as e:
                logger.warning(
                    "classification_attempt_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )
                if attempt < max_retries - 1:
                    continue
                else:
                    logger.error("classification_failed_max_retries", error=str(e))
                    raise LLMError(f"Failed to classify document after {max_retries} attempts: {str(e)}")

    def extract_information(self, text: str, doc_type: str) -> dict:
        """
        Extract structured information from document using type-specific schema.

        Args:
            text: Document text content
            doc_type: Document type (invoice, contract, receipt, report, unknown)

        Returns:
            Dictionary with extracted structured data

        Raises:
            LLMError: If extraction fails
        """
        if not text or not text.strip():
            raise LLMError("Document text is empty")

        if not doc_type:
            raise LLMError("Document type is required for extraction")

        # Truncate text
        max_chars = 30000
        text_truncated = text[:max_chars]

        prompt = get_extraction_prompt(text_truncated, doc_type)

        try:
            response = self.client.models.generate_content(
                model="models/gemini-3.1-flash-lite-preview",
                contents=prompt,
            )
            result = self._parse_json_response(response.text)
            logger.info("information_extracted", doc_type=doc_type)
            return result
        except Exception as e:
            logger.error("information_extraction_failed", error=str(e), doc_type=doc_type)
            raise LLMError(f"Failed to extract information: {str(e)}")

    def summarize_document(self, text: str, doc_type: str) -> dict:
        """
        Generate professional summary of document.

        Args:
            text: Document text content
            doc_type: Document type for context

        Returns:
            Dictionary with summary field

        Raises:
            LLMError: If summarization fails
        """
        if not text or not text.strip():
            raise LLMError("Document text is empty")

        # Truncate text
        max_chars = 30000
        text_truncated = text[:max_chars]

        prompt = get_summary_prompt(text_truncated, doc_type)

        try:
            response = self.client.models.generate_content(
                model="models/gemini-3.1-flash-lite-preview",
                contents=prompt,
            )
            result = self._parse_json_response(response.text)
            logger.info("document_summarized", doc_type=doc_type)
            return result
        except Exception as e:
            logger.error("document_summarization_failed", error=str(e))
            raise LLMError(f"Failed to summarize document: {str(e)}")

    @staticmethod
    def _parse_json_response(response_text: str) -> dict:
        """
        Strictly parse JSON response from Gemini.

        Args:
            response_text: Raw response text from API

        Returns:
            Parsed JSON as dictionary

        Raises:
            LLMError: If response cannot be parsed as valid JSON
        """
        if not response_text or not response_text.strip():
            raise LLMError("Empty response from API")

        # Clean up the response
        text = response_text.strip()

        try:
            # Try direct JSON parsing first
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.debug(
                "direct_json_parse_failed",
                error=str(e),
                response_preview=text[:200],
            )

        # Try to extract JSON from response (handle markdown code blocks, extra text, etc.)
        json_patterns = [
            r"```json\s*(.*?)```",  # Markdown code block with json tag
            r"```\s*(.*?)```",      # Code block without language
            r"(\{[\s\S]*\})",       # Raw JSON object (greedy)
        ]

        for pattern in json_patterns:
            try:
                json_match = re.search(pattern, text, re.DOTALL)
                if json_match:
                    extracted = json_match.group(1)
                    parsed = json.loads(extracted.strip())
                    logger.debug("json_extracted_from_response", pattern=pattern)
                    return parsed
            except (json.JSONDecodeError, IndexError, AttributeError) as e:
                logger.debug(
                    "json_pattern_extraction_failed",
                    pattern=pattern,
                    error=str(e),
                )
                continue

        # If all parsing attempts fail
        logger.error(
            "json_parsing_failed",
            response_length=len(text),
            response_preview=text[:500],
        )
        raise LLMError(
            f"Failed to parse JSON response from API. Response: {text[:300]}"
        )
