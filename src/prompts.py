"""
Production-ready prompts for document processing with Gemini LLM.

All prompts enforce:
- Strict JSON output format
- No explanatory text
- Null for missing fields (never empty strings or "N/A")
- ISO date formats
- Numeric values as numbers (not strings)
"""

# ============================================================================
# PROMPT 1: DOCUMENT TYPE CLASSIFICATION
# ============================================================================

CLASSIFICATION_PROMPT = """You are a document classification expert. Analyze the provided document text and classify it into ONE of these categories:
- invoice (bill for goods/services, contains amounts due)
- contract (agreement between parties with terms and conditions)
- receipt (proof of purchase/payment, itemized)
- report (analytical document with findings/data/summary)
- unknown (cannot be classified into above categories)

RULES:
1. Return ONLY valid JSON with no additional text
2. Base decision on document content, not file name
3. If document shows characteristics of multiple types, choose the PRIMARY purpose
4. If truly ambiguous, return "unknown"

OUTPUT FORMAT (JSON only):
{{
    "doc_type": "invoice|contract|receipt|report|unknown",
    "confidence": "high|medium|low",
    "reasoning": "Brief reason for classification"
}}

DOCUMENT TEXT:
{document_text}

Return only JSON."""

# ============================================================================
# PROMPT 2: TYPE-SPECIFIC FIELD EXTRACTION
# ============================================================================

EXTRACTION_PROMPT = """Extract structured data from the document. Output MUST be valid JSON with proper formatting.

CRITICAL RULES:
1. Output ONLY valid JSON - no explanation or extra text
2. Set any missing/unreadable field to null (NOT empty string, NOT "N/A", NOT "Unknown")
3. Numbers must be numeric type (e.g., 100 not "100" or "$100")
4. All amounts in document's native currency
5. Dates must be ISO 8601 format: YYYY-MM-DD (if only month/year given, use first day: YYYY-MM-01)
6. For arrays, use [] if empty, never use null for array type fields
7. Strings must be trimmed and clean

DOCUMENT TYPE: {doc_type}

EXTRACTION SCHEMA:

IF doc_type is "invoice":
{{
    "vendor_name": null|string,
    "vendor_contact": null|string,
    "invoice_number": null|string,
    "invoice_date": null|"YYYY-MM-DD",
    "due_date": null|"YYYY-MM-DD",
    "total_amount": null|number,
    "tax_amount": null|number,
    "currency": null|string,
    "line_items": [
        {{
            "description": string,
            "quantity": number,
            "unit_price": number,
            "total": number
        }}
    ],
    "payment_terms": null|string
}}

IF doc_type is "contract":
{{
    "parties": [string],
    "contract_date": null|"YYYY-MM-DD",
    "effective_date": null|"YYYY-MM-DD",
    "expiry_date": null|"YYYY-MM-DD",
    "contract_value": null|number,
    "key_terms": [string],
    "governing_law": null|string,
    "termination_clause": null|string
}}

IF doc_type is "receipt":
{{
    "store_name": null|string,
    "transaction_date": null|"YYYY-MM-DD",
    "transaction_time": null|"HH:MM:SS",
    "total_amount": null|number,
    "tax_amount": null|number,
    "currency": null|string,
    "items": [
        {{
            "name": string,
            "quantity": number,
            "price": number
        }}
    ],
    "payment_method": null|string,
    "receipt_number": null|string
}}

IF doc_type is "report":
{{
    "title": null|string,
    "author": null|string,
    "publication_date": null|"YYYY-MM-DD",
    "report_type": null|string,
    "summary_points": [string],
    "key_metrics": [
        {{
            "metric_name": string,
            "value": number|string
        }}
    ],
    "conclusion": null|string
}}

IF doc_type is "unknown":
{{
    "extracted_text": null|string,
    "identified_fields": {{}}
}}

DOCUMENT TEXT:
{document_text}

Return ONLY valid JSON matching the {doc_type} schema."""

# ============================================================================
# PROMPT 3: DOCUMENT SUMMARY
# ============================================================================

SUMMARY_PROMPT = """Generate a professional 2-4 sentence summary of this document.

REQUIREMENTS:
1. Include the document's primary purpose
2. Include key entities (company names, people, dates)
3. Include important amounts or metrics if present
4. Be factual - no assumptions or external knowledge
5. Use professional language
6. Return ONLY valid JSON

DOCUMENT TYPE: {doc_type}

DOCUMENT TEXT:
{document_text}

OUTPUT FORMAT (JSON only):
{{
    "summary": "2-4 sentence summary here"
}}

Return only JSON."""

# ============================================================================
# HELPER: PROMPT FORMATTER
# ============================================================================

def get_classification_prompt(document_text: str) -> str:
    """Format classification prompt with document text."""
    return CLASSIFICATION_PROMPT.format(document_text=document_text)


def get_extraction_prompt(document_text: str, doc_type: str) -> str:
    """Format extraction prompt with document text and type."""
    return EXTRACTION_PROMPT.format(
        document_text=document_text,
        doc_type=doc_type
    )


def get_summary_prompt(document_text: str, doc_type: str) -> str:
    """Format summary prompt with document text and type."""
    return SUMMARY_PROMPT.format(
        document_text=document_text,
        doc_type=doc_type
    )


# ============================================================================
# PROMPT CONFIGURATION
# ============================================================================

GEMINI_CONFIG = {
    "temperature": 0.1,  # Low temp for consistent JSON output
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2048,
}

# Strict JSON mode settings
JSON_CONFIG = {
    "temperature": 0.0,  # Deterministic for JSON
    "max_output_tokens": 4096,
}
