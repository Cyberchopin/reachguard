"""Explicit local audio upload: python scripts/stream_wav.py consented.wav."""
import asyncio
import json
import sys
import wave
from websockets.asyncio.client import connect


async def main(path):
    with wave.open(path, "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
            raise ValueError("Use mono 16kHz PCM16 WAV")
        async with connect("ws://127.0.0.1:8000/v1/stream/audio") as ws:
            async def send():
                while chunk := audio.readframes(1600):
                    chunk = chunk.ljust(3200, b"\0")
                    await ws.send(chunk)
                    await asyncio.sleep(.1)
                await ws.send('{"type":"stop"}')
            async def receive():
                async for message in ws:
                    print(message)
            async with asyncio.TaskGroup() as group:
                group.create_task(send())
                group.create_task(receive())


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
