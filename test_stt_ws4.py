"""Test STT WebSocket - using async for iteration (the __aiter__ method in SDK)."""
import asyncio
import os
import base64
import time
import glob
from dotenv import load_dotenv
load_dotenv()

from sarvamai import AsyncSarvamAI

async def test():
    client = AsyncSarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
    
    recordings = glob.glob("recordings/*.wav")
    if not recordings:
        print("No recordings found")
        return
        
    test_file = recordings[0]
    print(f"Using: {test_file}")
    
    # Check file size
    file_size = os.path.getsize(test_file)
    print(f"File size: {file_size} bytes")
    
    with open(test_file, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")
    
    print(f"Base64 encoded length: {len(audio_data)}")
    
    t0 = time.time()
    print(f"[{time.time()-t0:.2f}s] Connecting...")
    
    async with client.speech_to_text_streaming.connect(
        model="saaras:v3",
        mode="transcribe",
        language_code="en-IN",
    ) as ws:
        print(f"[{time.time()-t0:.2f}s] Connected!")
        print(f"WebSocket type: {type(ws)}")
        
        # Send audio FIRST before waiting for response
        print(f"[{time.time()-t0:.2f}s] Sending audio...")
        await ws.transcribe(
            audio=audio_data,
            encoding="audio/wav",
            sample_rate=16000
        )
        
        print(f"[{time.time()-t0:.2f}s] Flushing...")
        await ws.flush()
        
        # Use __aiter__ (async for) which is the standard iteration pattern
        print(f"[{time.time()-t0:.2f}s] Waiting for messages via async for...")
        
        async def receive_with_timeout():
            async for message in ws:
                print(f"[{time.time()-t0:.2f}s] Got message!")
                print(f"  Type: {type(message)}")
                print(f"  Value: {message}")
                
                # Check if this is a transcription response
                if hasattr(message, 'type'):
                    print(f"  message.type: {message.type}")
                if hasattr(message, 'data'):
                    print(f"  message.data: {message.data}")
                    if hasattr(message.data, 'transcript'):
                        print(f"  TRANSCRIPT: {message.data.transcript}")
                        return message.data.transcript
                        
        try:
            transcript = await asyncio.wait_for(receive_with_timeout(), timeout=10)
            print(f"[{time.time()-t0:.2f}s] DONE! Transcript: {transcript}")
        except asyncio.TimeoutError:
            print(f"[{time.time()-t0:.2f}s] TIMEOUT - no message received within 10s")
        
asyncio.run(test())

