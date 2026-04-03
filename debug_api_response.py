#!/usr/bin/env python
"""Debug script to test Gemini API response format."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import config
from src.llm import GeminiClient
from src.extraction import TextExtractor
import json

def test_classification_response():
    """Test what the Gemini API actually returns."""

    print("=" * 70)
    print("TESTING GEMINI API RESPONSE FORMAT")
    print("=" * 70)

    # Initialize
    llm = GeminiClient(config.GEMINI_API_KEY)

    # Get sample text
    sample_files = list(Path("documents").glob("*.txt"))
    if not sample_files:
        sample_files = list(Path("documents").glob("*.pdf"))

    if not sample_files:
        print("❌ No sample files found")
        return

    sample_file = sample_files[0]
    print(f"\n📄 Using: {sample_file.name}")

    # Extract text
    extractor = TextExtractor()
    text = extractor.extract(str(sample_file))
    text = text[:1000]  # Small sample for testing

    print(f"✅ Extracted {len(text)} characters\n")

    # Test raw API call
    print("🔍 Making raw API call to Gemini...\n")

    from src.prompts import get_classification_prompt

    prompt = get_classification_prompt(text)
    print(f"Prompt length: {len(prompt)} chars\n")

    try:
        response = llm.client.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=prompt,
        )

        print("📝 Raw Response Text:")
        print("-" * 70)
        print(response.text)
        print("-" * 70)
        print(f"\nResponse length: {len(response.text)} characters")
        print(f"Response type: {type(response.text)}")

        # Try to parse it
        print("\n🔄 Attempting to parse as JSON...\n")
        try:
            parsed = json.loads(response.text)
            print("✅ Successfully parsed as JSON!")
            print(json.dumps(parsed, indent=2))
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"First 200 chars: {response.text[:200]}")

    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_classification_response()
