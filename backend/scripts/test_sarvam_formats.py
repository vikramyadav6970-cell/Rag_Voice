"""Debug script to inspect Sarvam API transcription across audio formats and parameters."""

import asyncio
import os
import sys
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_KEY = os.getenv("SARVAM_API_KEY")
print("API_KEY:", API_KEY[:10] + "...")

async def test_sarvam_api():
    # Generate 2 seconds of synthetic speech-like WAV
    import io
    import wave
    import struct
    import math

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        # 16000 samples/sec for 2 sec
        frames = bytearray()
        for i in range(32000):
            # 440Hz tone
            val = int(32767.0 * 0.3 * math.sin(2.0 * math.pi * 440.0 * i / 16000.0))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    wav_bytes = buf.getvalue()

    headers = {"api-subscription-key": API_KEY}
    
    # Test 1: standard saaras:v3
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data = {"model": "saaras:v3", "language_code": "hi-IN"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post("https://api.sarvam.ai/speech-to-text", headers=headers, files=files, data=data)
        print("\nTest 1 (saaras:v3, hi-IN):", res.status_code, res.text)

    # Test 2: saaras:v3 without language_code (auto-detect)
    files2 = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data2 = {"model": "saaras:v3"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        res2 = await client.post("https://api.sarvam.ai/speech-to-text", headers=headers, files=files2, data=data2)
        print("\nTest 2 (saaras:v3 auto):", res2.status_code, res2.text)

asyncio.run(test_sarvam_api())
