#!/usr/bin/env python
"""Test script to verify LLM pipeline is working correctly."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from src.llm import GeminiClient
from src.extraction import TextExtractor
from src.prompts import get_classification_prompt, get_extraction_prompt

def test_llm_pipeline():
    """Test the complete LLM pipeline with actual document."""
    print("=" * 60)
    print("TESTING LLM PIPELINE WITH ACTUAL DOCUMENT")
    print("=" * 60)

    # Initialize LLM client
    try:
        llm = GeminiClient(config.GEMINI_API_KEY)
        print("✅ LLM client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize LLM: {e}")
        return

    # Get a sample document
    sample_files = list(Path("documents").glob("*.txt"))
    if not sample_files:
        sample_files = list(Path("documents").glob("*.pdf"))

    if not sample_files:
        print("❌ No sample files found in documents/ folder")
        return

    sample_file = sample_files[0]
    print(f"\n📄 Testing with: {sample_file.name}")

    # Extract text
    try:
        extractor = TextExtractor()
        text = extractor.extract(str(sample_file))
        print(f"✅ Text extracted ({len(text)} characters)")
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")
        return

    # Test classification
    print("\n🔍 Testing classification...")
    try:
        classification = llm.classify_document(text[:5000])
        print(f"✅ Classification successful:")
        print(f"   - doc_type: {classification.get('doc_type')}")
        print(f"   - confidence: {classification.get('confidence')}")
        print(f"   - reasoning: {classification.get('reasoning', 'N/A')[:100]}...")
    except Exception as e:
        print(f"❌ Classification failed: {e}")
        return

    # Test extraction
    print("\n📊 Testing extraction...")
    doc_type = classification.get("doc_type", "unknown")
    try:
        extraction = llm.extract_information(text[:5000], doc_type)
        print(f"✅ Extraction successful:")
        print(f"   - Fields extracted: {len(extraction)} keys")
        for key in list(extraction.keys())[:5]:
            print(f"     • {key}: {str(extraction[key])[:50]}...")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    # Test summary
    print("\n📝 Testing summary...")
    try:
        summary = llm.summarize_document(text[:5000], doc_type)
        print(f"✅ Summary successful:")
        print(f"   {summary.get('summary', 'N/A')[:100]}...")
    except Exception as e:
        print(f"❌ Summary failed: {e}")
        return

    print("\n" + "=" * 60)
    print("✅ ALL LLM TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_llm_pipeline()
