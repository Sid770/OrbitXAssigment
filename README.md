# AI Document Processor

A production-grade AI document processing system that automatically classifies, extracts structured data, and summarizes documents using Google Gemini LLM.


---

## Architecture Overview

### System Flow Diagram

```
User Upload (Web UI / API)
    ↓
[Document Ingestion]
  - File validation
  - Format check (.pdf, .txt)
  - Size validation (max 50MB)
    ↓
[Text Extraction]
  - PDF → text (pdfplumber)
  - TXT → direct read
  - Empty document detection
    ↓
[Document Classification] (Gemini LLM)
  - Analyze content
  - Determine doc type (Invoice/Contract/Receipt/Report/Unknown)
  - Calculate confidence score
    ↓
[Type-Specific Extraction] (Gemini LLM)
  - Extract schema-specific fields
  - Parse JSON response with retry logic
  - Populate structured fields
    ↓
[Summarization] (Gemini LLM)
  - Generate 2-4 sentence professional summary
  - Capture key information
    ↓
[Output & Storage]
  - Save individual document JSON
  - Save combined pipeline results
  - Return to frontend
    ↓
Response (JSON formatted results)
```

### Component Architecture

```
main.py (FastAPI)
├── POST /upload-and-process
│   └── PipelineOrchestrator
│       ├── DocumentIngester (src/ingestion.py)
│       ├── TextExtractor (src/extraction.py)
│       ├── GeminiClient (src/llm.py)
│       └── OutputWriter (src/output.py)
├── GET /health
├── GET /results
└── Static Files (Frontend)
    ├── index.html
    ├── styles.css
    └── app.js

CLI Interface (cli.py)
└── Same PipelineOrchestrator

Config Management (config.py)
└── Environment variables, paths, API keys
```

---

## Tools & Libraries Used

| Tool | Purpose | Version |
|------|---------|---------|
| **Google Gemini API** | LLM for classification, extraction, summarization | Latest |
| **FastAPI** | REST API framework, static file serving | ^0.104.1 |
| **Uvicorn** | ASGI server | ^0.24.0 |
| **pdfplumber** | PDF text extraction | ^0.10.3 |
| **Pydantic** | Data validation, request/response models | ^2.4.2 |
| **python-dotenv** | Environment variable management | ^1.0.0 |
| **structlog** | Structured JSON logging | ^23.2.0 |
| **google-genai** | Gemini SDK Python client | Latest |

**Frontend**: Vanilla HTML/CSS/JavaScript (zero framework dependencies)

---

## Design Tradeoffs

### 1. **Vanilla Frontend vs Modern Framework**
   - **Choice**: Vanilla HTML/CSS/JavaScript
   - **Tradeoff**:
     - ✅ Zero dependencies, faster load time (~20KB)
     - ✅ Easy to customize, no build step needed
   - **Decision**: Production simplicity > dev convenience

### 2. **Individual Document Files vs Single Pipeline Result**
   - **Choice**: Save both (individual + combined)
   - **Tradeoff**:
     - ✅ Individual files for easy access to single documents
     - ✅ Combined file for batch analytics
   - **Decision**: Flexibility > storage optimization

### 3. **Retry Logic: 2 Retries vs Infinite**
   - **Choice**: Maximum 2 retries for JSON parsing
   - **Tradeoff**:
     - ✅ Prevents infinite loops, predictable behavior
     - ✅ Fails fast, user knows result quickly
   - **Decision**: Reliability > perfection

### 4. **Null Fields vs Default Values**
   - **Choice**: Return `null` for missing fields
   - **Tradeoff**:
     - ✅ Explicit about missing data
     - ✅ Downstream systems see absence clearly
   - **Decision**: Data integrity > convenience

### 5. **Synchronous Processing vs Async Queues**
   - **Choice**: Synchronous (FastAPI async wrapper)
   - **Tradeoff**:
     - ✅ Simple, no message queue infrastructure
     - ✅ Works for 1-10 files per request
   - **Decision**: Simplicity for typical use case

### 6. **Type Detection First vs Direct Extraction**
   - **Choice**: Classify first, then type-specific extraction
   - **Tradeoff**:
     - ✅ Better accuracy (context-aware extraction)
     - ✅ Handles unknown documents gracefully
   - **Decision**: Quality > speed

---

## How to Run Locally

### Prerequisites
- Python 3.9+
- Google Gemini API key (free: https://aistudio.google.com/apikey)

### Step 1: Setup Environment

```bash
# Navigate to project directory
cd OrbitXAssignment

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure API Key

```bash
# Create .env file (or update existing)
cp .env.example .env

# Edit .env and add your Gemini API key:
GEMINI_API_KEY=your_api_key_here
```

### Step 4: Run Application

**Option A: Web UI (Recommended)**
```bash
python main.py
# Visit: http://localhost:8000
```

**Option B: Command Line**
```bash
# First generate sample documents
python generate_samples.py

# Process folder
python cli.py --folder ./documents
```

**Option C: REST API**
```bash
# Start server
python main.py

# In another terminal, upload files
curl -X POST http://localhost:8000/upload-and-process \
  -F "files=@documents/invoice_001.txt"
```

### Step 5: Check Results

Results are saved in `./outputs/` folder as JSON files:
- `document_filename_timestamp.json` - Individual document
- `pipeline_results_timestamp.json` - Combined results

---

## Sample Output

### Input Document (invoice_001.txt)
```
Invoice #INV-2024-001
=====================

Date: January 15, 2024
Due Date: February 15, 2024

Bill To:
Acme Corporation
123 Business Street
Suite 100
New York, NY 10001

Description of Services:
- Consulting Services (40 hours @ $150/hr): $6,000
- Software Development (80 hours @ $200/hr): $16,000
- Project Management (20 hours @ $100/hr): $2,000

Subtotal: $24,000
Tax (10%): $2,400
Total Due: $26,400

Payment Terms: Net 30
Please remit payment to: billing@company.com
```

### Output (document_invoice_001_20260403_172510.json)
```json
{
  "file": "invoice_001.pdf",
  "doc_type": "invoice",
  "extracted_fields": {
    "vendor_name": null,
    "vendor_contact": "billing@company.com",
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-15",
    "total_amount": 26400,
    "tax_amount": 2400,
    "currency": "USD",
    "line_items": [
      {
        "description": "Consulting Services",
        "quantity": 40,
        "unit_price": 150,
        "total": 6000
      },
      {
        "description": "Software Development",
        "quantity": 80,
        "unit_price": 200,
        "total": 16000
      },
      {
        "description": "Project Management",
        "quantity": 20,
        "unit_price": 100,
        "total": 2000
      }
    ],
    "payment_terms": "Net 30"
  },
  "summary": "Invoice #INV-2024-001, issued to Acme Corporation on January 15, 2024, details charges for consulting, software development, and project management services. The document reflects a total amount due of $26,400, which includes a 10% tax assessment on the $24,000 subtotal. Payment is required by the due date of February 15, 2024.",
  "confidence": "high",
  "errors": [],
  "text_length": 448,
  "processing_time_seconds": 7.03
}
```

### Email Processing Example

**Input**: email_format.pdf (customer inquiry email)

**Output**:
```json
{
  "file": "email_format.pdf",
  "doc_type": "email",
  "extracted_fields": {
    "sender": "John Smith",
    "sender_email": "John.Smith@client.com",
    "company": "Acme Corporation",
    "job_title": "CTO",
    "date": "2024-01-18",
    "subject": "Questions about Implementation Timeline",
    "phone": "(555) 123-4567"
  },
  "summary": "On January 18, 2024, John Smith, CTO of Acme Corporation, initiated an inquiry regarding the implementation process for the provider's platform. The correspondence seeks clarification on the project timeline, support services, integration capabilities, and enterprise licensing options as part of their formal solution evaluation process.",
  "confidence": "high",
  "errors": [],
  "text_length": 819,
  "processing_time_seconds": 10.78
}
```

### Pipeline Report (Combined Results)
```json
{
  "pipeline_report": {
    "timestamp": "2026-04-03T17:25:10.636601",
    "summary": "Processed 2/2 files, 0 failed, 0 skipped",
    "statistics": {
      "total_files": 2,
      "processed": 2,
      "successful": 2,
      "failed": 0,
      "skipped": 0,
      "elapsed_seconds": 17.82
    }
  },
  "documents": [
    { /* invoice document */ },
    { /* email document */ }
  ]
}
```

---

## Project Structure

```
OrbitXAssignment/
├── src/
│   ├── ingestion.py       # File loading & validation
│   ├── extraction.py      # PDF/TXT text extraction
│   ├── llm.py            # Gemini API client
│   ├── pipeline.py       # 10-step orchestration
│   ├── output.py         # JSON output writer
│   ├── prompts.py        # LLM prompts
│   └── utils/
│       ├── logging.py    # Structured logging
│       └── errors.py     # Custom exceptions
├── static/
│   ├── index.html        # Web UI
│   ├── styles.css        # Styling
│   └── app.js           # Frontend logic
├── documents/            # Sample documents
├── outputs/              # Results (auto-created)
├── main.py              # FastAPI server
├── cli.py               # CLI interface
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
└── README.md            # This file
```

---

## Features

✅ **Multi-format support** - PDF and TXT files
✅ **Auto-classification** - Classifies document types
✅ **Type-specific extraction** - Schema-aware field extraction
✅ **Summarization** - 2-4 sentence summaries
✅ **Error resilience** - Handles corrupted files, API failures
✅ **Structured logging** - JSON logs for debugging
✅ **Web UI** - Drag-drop interface with progress tracking
✅ **REST API** - Full HTTP interface
✅ **CLI** - Command-line processing
✅ **Individual & combined output** - Flexible result formats

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key not configured" | Check `.env` has valid `GEMINI_API_KEY` |
| "Connection refused on :8000" | Port 8000 in use; kill process or change port |
| "Module not found" | Missing pip install; run `pip install -r requirements.txt` |
| "PDF extraction fails" | Try with TXT file; PDF may be corrupted |
| "Web UI not loading" | Hard refresh browser (Ctrl+Shift+R) |

---

**Ready to start?** Run `python main.py` and visit http://localhost:8000 🚀
