"""Test TTS WebSocket streaming - following official Sarvam docs."""
import asyncio
import os
import base64
import time
from dotenv import load_dotenv
load_dotenv()

from sarvamai import AsyncSarvamAI, AudioOutput, EventResponse

async def test():
    client = AsyncSarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
    
    test_text = "Hello! This is a test of the WebSocket streaming text to speech system. I hope it works well."
    
    t0 = time.time()
    print(f"[{time.time()-t0:.2f}s] Connecting with send_completion_event=True...")
    
    async with client.text_to_speech_streaming.connect(
        model="bulbul:v3",
        send_completion_event=True  # IMPORTANT: Required to receive "final" event
    ) as ws:
        print(f"[{time.time()-t0:.2f}s] Connected!")
        
        # Configure
        await ws.configure(
            target_language_code="en-IN",
            speaker="shubh",
            output_audio_codec="mp3",
            pace=1.1
        )
        print(f"[{time.time()-t0:.2f}s] Configured")
        
        # Send text
        await ws.convert(test_text)
        print(f"[{time.time()-t0:.2f}s] Sent text")
        
        # Flush to force processing
        await ws.flush()
        print(f"[{time.time()-t0:.2f}s] Flushed")
        
        # Receive chunks
        chunk_count = 0
        total_bytes = 0
        first_chunk_time = None
        
        async for message in ws:
            if isinstance(message, AudioOutput):
                chunk_count += 1
                audio_chunk = base64.b64decode(message.data.audio)
                total_bytes += len(audio_chunk)
                if first_chunk_time is None:
                    first_chunk_time = time.time() - t0
                    print(f"[{first_chunk_time:.2f}s] First chunk received ({len(audio_chunk)} bytes)")
            elif isinstance(message, EventResponse):
                print(f"[{time.time()-t0:.2f}s] Event: {message.data.event_type}")
                if message.data.event_type == "final":
                    print(f"[{time.time()-t0:.2f}s] Received final event - breaking loop")
                    break
        
        print(f"\n=== SUMMARY ===")
        print(f"Total time: {time.time()-t0:.2f}s")
        print(f"First chunk: {first_chunk_time:.2f}s")
        print(f"Chunks: {chunk_count}")
        print(f"Total audio: {total_bytes} bytes")

asyncio.run(test())

