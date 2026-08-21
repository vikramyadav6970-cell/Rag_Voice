"""Test script for Sarvam AI Speech-to-Text (STT) Client."""

import asyncio
import io
import math
import os
import struct
import sys
import wave

from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.stt import transcribe

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def generate_synthetic_wav_bytes(duration_sec: float = 1.5, sample_rate: int = 16000) -> bytes:
    """Generate a clean synthetic sine-wave WAV in memory for API testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        # Generate 440Hz tone with envelope
        n_samples = int(duration_sec * sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = float(i) / sample_rate
            val = int(16000 * math.sin(2.0 * math.pi * 440.0 * t))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


async def run_stt_test() -> None:
    """Execute live test against Sarvam AI STT API."""
    print("=" * 65)
    print("TESTING SARVAM AI SPEECH-TO-TEXT (STT) INTEGRATION")
    print("=" * 65 + "\n")

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("ERROR: SARVAM_API_KEY is not set in backend/.env")
        sys.exit(1)

    print(f"API Key present: {api_key[:8]}... (length: {len(api_key)})")
    
    # 1. Test with synthetic WAV
    print("Generating synthetic 1.5s 16kHz test WAV...")
    wav_bytes = generate_synthetic_wav_bytes(duration_sec=1.5, sample_rate=16000)
    print(f"Audio payload size: {len(wav_bytes):,} bytes\n")

    print("Calling Sarvam STT API (Saaras v3) with Hindi language hint...")
    result = await transcribe(audio_bytes=wav_bytes, language_hint="hi-IN")

    print("\n" + "-" * 65)
    print("SARVAM STT RESPONSE")
    print("-" * 65)
    print(f"Success           : {result.get('success')}")
    print(f"Observed Latency  : {result.get('latency_ms')} ms")
    print(f"Transcript        : '{result.get('text')}'")
    print(f"Detected Language : {result.get('detected_language')}")
    if result.get("error"):
        print(f"Error Details     : {result.get('error')}")

    print("\n" + "=" * 65)
    print("STT CLIENT VERIFICATION FINISHED")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_stt_test())
