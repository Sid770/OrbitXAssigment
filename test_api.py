"""Test script to verify Gemini API is working."""
import os
from dotenv import load_dotenv
import google.genai

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

print("=" * 60)
print("GEMINI API TEST")
print("=" * 60)

# Check if API key exists
if not API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

print(f"✅ API Key found: {API_KEY[:20]}...{API_KEY[-10:]}")

# Try to initialize client
try:
    client = google.genai.Client(api_key=API_KEY)
    print("✅ Gemini client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize client: {e}")
    exit(1)

# Test API call
print("\n📝 Testing API call with gemini-3.1-flash-lite-preview...")
print("-" * 60)

try:
    response = client.models.generate_content(
        model="models/gemini-3.1-flash-lite-preview",
        contents="Say hello in 5 words",
    )

    print("✅ API Call successful!")
    print(f"\nResponse:\n{response.text}")
    print("\n" + "=" * 60)
    print("✅ YOUR GEMINI API IS WORKING!")
    print("=" * 60)

except Exception as e:
    print(f"❌ API Call failed: {e}")
    print("\nCommon issues:")
    print("  - Invalid API key")
    print("  - API not enabled in Google Cloud")
    print("  - Rate limit exceeded")
    print("  - Model name incorrect")
    exit(1)
