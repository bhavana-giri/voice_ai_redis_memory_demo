"""Test full STT + Agent + TTS flow through the API."""
import asyncio
import os
import base64
import time
import glob
import requests
from dotenv import load_dotenv
load_dotenv()

def test_full_conversation():
    """Test the complete voice conversation flow."""
    
    # Find a test audio file
    recordings = glob.glob("recordings/*.wav")
    if not recordings:
        print("No recordings found in recordings/ directory")
        return
    
    test_file = recordings[0]
    print(f"Using audio file: {test_file}")
    
    # Read and encode audio
    with open(test_file, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    print(f"Audio base64 length: {len(audio_base64)}")
    
    # Test the agent/chat endpoint with audio
    print("\n=== Testing /api/agent/chat with audio ===")
    t0 = time.time()
    
    response = requests.post(
        "http://localhost:8080/api/agent/chat",
        json={
            "audio_base64": audio_base64,
            "user_id": "test_user",
            "session_id": "test_session",
            "language_code": "en-IN"
        },
        timeout=30
    )
    
    t1 = time.time()
    
    print(f"\nTotal API response time: {t1-t0:.2f}s")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n=== Response ===")
        print(f"Transcript: {data.get('transcript', 'N/A')}")
        print(f"Response text: {data.get('response_text', 'N/A')[:200]}...")
        print(f"Has audio: {bool(data.get('audio_base64'))}")
        if data.get('audio_base64'):
            audio_bytes = len(base64.b64decode(data['audio_base64']))
            print(f"Audio size: {audio_bytes} bytes")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_full_conversation()

