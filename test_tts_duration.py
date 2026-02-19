"""Test TTS duration to understand why it takes so long."""
import asyncio
import time
from src.audio_handler import AudioHandler

handler = AudioHandler()

# Test responses of different lengths
test_texts = [
    ("Very short", "Yes, you have 3 meetings today."),
    ("Short", "You have 3 meetings today. The first one is at 10 AM with the engineering team."),
    ("Medium", "Today you have a standup at 10 AM, a product review at 2 PM, and a one-on-one with your manager at 4 PM. Would you like details on any of these?"),
]

async def test():
    print("=== TTS Duration Test ===\n")
    
    for name, text in test_texts:
        print(f"{name} ({len(text)} chars): \"{text[:50]}...\"")
        
        # Streaming TTS
        t0 = time.time()
        audio = await handler.text_to_speech_stream_full(text, "en-IN", "shubh")
        streaming_time = time.time() - t0
        
        # Non-streaming TTS for comparison
        t1 = time.time()
        audio2 = handler.text_to_speech(text, "en-IN", "shubh")
        rest_time = time.time() - t1
        
        print(f"  Streaming: {streaming_time:.2f}s | REST: {rest_time:.2f}s | Audio: {len(audio)} bytes")
        print()

asyncio.run(test())

