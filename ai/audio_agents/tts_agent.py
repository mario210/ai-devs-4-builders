import asyncio
from loguru import logger
from typing import Optional
import edge_tts

class EdgeTTSAgent:
    """
    TTS Agent using edge-tts (Microsoft voices)
    """

    def __init__(
            self,
            voice: str = "pl-PL-MarekNeural",
            rate: str = "+0%",
            volume: str = "+0%"
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume

        logger.debug(f"Initialized EdgeTTSAgent with voice={voice}")

    async def generate_audio_async(
            self,
            text: str,
            voice: Optional[str] = None
    ) -> bytes:
        try:
            current_voice = voice or self.voice

            #logger.debug(f"Generating TTS: {text[:60]}...")

            communicate = edge_tts.Communicate(
                text=text,
                voice=current_voice,
                rate=self.rate,
                volume=self.volume
            )

            audio_chunks = bytearray()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.extend(chunk["data"])

            return bytes(audio_chunks)

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""

    def generate_audio(self, text: str, voice: Optional[str] = None) -> bytes:
        return asyncio.run(self.generate_audio_async(text, voice))
