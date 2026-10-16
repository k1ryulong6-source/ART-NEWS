"""Regenerate the promo's English voiceover (promo/voice/l1.mp3 … l6.mp3).

Voice: Microsoft Edge neural voice en-US-GuyNeural, rate +8 %, pitch +6 Hz (chosen by the
user from three candidates). Needs `pip install edge-tts` and network access. The licence
for using this service in public releases is unclear; for a public release, re-record
LINES with a human voice (same file names, similar lengths) and rebuild the score.

  python promo/voice.py [--cafile /path/to/proxy-ca.crt]
"""
from __future__ import annotations

import argparse
import asyncio
import ssl
from pathlib import Path

LINES = [
    "Good evening, citizens of tomorrow! You're watching Intermission TV!",
    "Every two hours, our marvelous news machine gathers the latest in film, photography and art, from every corner of the globe!",
    "From Tokyo to London, Busan to New York — the world's culture headlines meet right here!",
    "Film! Photography! Art! Step right up — the stories are fresh off the wire!",
    "And with \"A Kind of Attention\", we look farther — to the corners of the map you've never seen!",
    "Intermission — art, film and photography news from around the world. Mujian rest dot work! Stay curious, citizens!",
]
VOICE, RATE, PITCH = "en-US-GuyNeural", "+8%", "+6Hz"


async def main(cafile: str | None) -> None:
    import edge_tts
    import edge_tts.communicate as communicate

    if cafile:
        communicate._SSL_CTX = ssl.create_default_context(cafile=cafile)
    out = Path(__file__).with_name("voice")
    out.mkdir(exist_ok=True)
    for i, line in enumerate(LINES, 1):
        await edge_tts.Communicate(line, VOICE, rate=RATE, pitch=PITCH).save(str(out / f"l{i}.mp3"))
        print(f"wrote voice/l{i}.mp3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cafile")
    asyncio.run(main(parser.parse_args().cafile))
