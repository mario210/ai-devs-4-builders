from loguru import logger
import tempfile
from typing import Optional
from faster_whisper import WhisperModel

class STTAgent:
    """
    Speech-to-Text agent using local Whisper (faster-whisper).
    """

    def __init__(
        self,
        model_size: str = "small",  # tiny, base, small, medium, large
        device: str = "cpu",        # "cpu" albo "cuda"
        compute_type: str = "int8"  # int8 dla CPU, float16 dla GPU
    ):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

        logger.debug(f"STTAgent initialized with Whisper model: '{model_size}'")

    def transcribe_audio(
        self,
        audio_content: bytes,
        language: Optional[str] = "pl"
    ) -> str:
        """
        Transcribes audio bytes using Whisper.

        Args:
            audio_content: audio bytes (mp3/wav)
            language: language code (e.g. "pl")

        Returns:
            str: transcribed text
        """

        try:
            logger.debug("STTAgent: Transcribing audio...")

            # Whisper potrzebuje pliku → zapis tymczasowy
            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as temp_audio_file:
                temp_audio_file.write(audio_content)
                temp_audio_file.flush()

                segments, info = self.model.transcribe(
                    temp_audio_file.name,
                    language=language
                )

                text = "".join([segment.text for segment in segments])

            #logger.debug(f"STTAgent result: {text}")
            return text

        except Exception as e:
            logger.error(f"STTAgent error: {e}")
            return ""