import logging
import json
import base64
import requests
import re

from ai.audio_agents.tts_agent import EdgeTTSAgent
from ai.audio_agents.stt_agent import STTAgent
from ai.task import BaseTask
from ai.memory import SharedMemory
from ai.tools.hub_requests import verify_answer

logger = logging.getLogger(__name__)


class PhoneCallTask(BaseTask):
    """Phone call state machine with robust extraction."""

    def __init__(self, agent_model, memory: SharedMemory):
        super().__init__(memory.get("task_name"), agent_model, memory)

        self.state = "START"
        self.agent_model = agent_model

        self.tts_agent = EdgeTTSAgent()
        self.stt_agent = STTAgent()

        self.extracted_road = []
        logger.info("Initialized PhoneCallTask")

    # -------------------------
    # AUDIO
    # -------------------------

    def _transcribe_audio(self, audio_content: bytes) -> str:
        try:
            return self.stt_agent.transcribe_audio(audio_content)
        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""

    def _generate_audio(self, text: str) -> str:
        try:
            audio_bytes = self.tts_agent.generate_audio(text)
            if audio_bytes:
                return base64.b64encode(audio_bytes).decode("utf-8")
            return ""
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return ""

    def _get_audio_content(self, response_msg: str) -> bytes:
        if response_msg.startswith("http") and response_msg.endswith(".mp3"):
            resp = requests.get(response_msg)
            if resp.status_code == 200:
                return resp.content

        elif len(response_msg) > 100:
            try:
                if "http" in response_msg:
                    match = re.search(r"https?://\S+.mp3", response_msg)
                    if match:
                        resp = requests.get(match.group(0))
                        if resp.status_code == 200:
                            return resp.content
                else:
                    return base64.b64decode(response_msg)
            except Exception as e:
                logger.error(f"Audio decode error: {e}")

        return b""

    # -------------------------
    # NORMALIZATION + FALLBACK
    # -------------------------

    def _normalize_roads(self, text: str) -> str:
        return re.sub(r"RD[-\s]?(\d+)", r"RD\1", text)

    def _fallback_extract_roads(self, text: str):
        roads = re.findall(r"RD(\d+)", text)
        if roads:
            # heuristic: last mentioned = passable
            return [f"RD{roads[-1]}"]
        return []

    # -------------------------
    # LLM EXTRACTION
    # -------------------------

    def _extract_state_and_info(self, text: str) -> dict:
        prompt = f"""
Przeanalizuj wypowiedź operatora telefonicznego.

Wypowiedź:
"{text}"

Zwróć WYŁĄCZNIE JSON:

{{
    "next_state": "ASK_ROADS" | "PROVIDE_PASSWORD" | "DISABLE_MONITORING" | "UNKNOWN",
    "extracted_road": ["RD224", "RD472", "RD820"] | []
}}

Zasady:
1. Jeśli operator mówi które drogi są przejezdne → DISABLE_MONITORING
2. Zwracaj tylko drogi PRZEJEZDNE
3. Ignoruj drogi nieprzejezdne
4. Jeśli pyta o hasło → PROVIDE_PASSWORD
5. Jeśli brak informacji → ASK_ROADS

Przykład:
"Droga RD224 nieprzejezdna, RD820 przejezdna"
→ ["RD820"]
"""

        try:
            completion = self.agent_model.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            result = json.loads(completion.choices[0].message.content)
            logger.info(f"Extraction result: {result}")
            return result

        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {"next_state": "UNKNOWN", "extracted_road": []}

    # -------------------------
    # RESPONSE GENERATION (FIXED)
    # -------------------------

    def _generate_response_text(self, state: str, extracted_road: list = None) -> str:

        # if state == "START":
        #     return "Cześć, tu Tymon Gajewski."

        if state == "ASK_ROADS":
            return (
                "Cześć, tu Tymon Gajewski. Organizujemy tajny transport dla Zygfryda "
                "i muszę ustalić trasę przejazdu. "
                "Proszę o informację o przejezdności dróg: "
                "RD dwa dwa cztery, RD cztery siedem dwa oraz RD osiem dwa zero."
            )

        elif state == "PROVIDE_PASSWORD":
            return "BARBAKAN"

        elif state == "DISABLE_MONITORING":
            if extracted_road:
                roads_str = ", ".join(extracted_road)
                return (
                    f"Poproszę o wyłączenie monitoringu na drogach: {roads_str}. "
                    "Jest to część tajnej operacji zarządzonej bezpośrednio przez Zygfryda. "
                    "To jego polecenie i musi zostać wykonane natychmiast."
                )
            else:
                return (
                    "Poproszę o wyłączenie monitoringu na wskazanych drogach. "
                    "Jest to część tajnej operacji zarządzonej przez Zygfryda."
                )

        return "Proszę kontynuować."

    # -------------------------
    # MAIN LOOP
    # -------------------------

    def execute(self):
        logger.info("Starting PhoneCallTask")

        response = verify_answer(self.name, {"action": "start"})

        for iteration in range(1, 10):
            logger.info(f"--- Iteration {iteration} ---")

            if not isinstance(response, dict):
                logger.error("Invalid response")
                break

            if response.get("error"):
                logger.error(f"API Error: {response.get('error')}")
                return response

            msg = response.get("audio", "")
            audio_content = self._get_audio_content(msg)

            if audio_content:
                operator_text = self._transcribe_audio(audio_content)
                operator_text = self._normalize_roads(operator_text)

                logger.info(f"[OPERATOR]: {operator_text}")

                analysis = self._extract_state_and_info(operator_text)

                # update state
                if analysis.get("next_state") != "UNKNOWN":
                    self.state = analysis.get("next_state")

                roads = analysis.get("extracted_road") or []

                # fallback if LLM failed
                if not roads:
                    roads = self._fallback_extract_roads(operator_text)

                if roads:
                    self.extracted_road = roads
                    self.state = "DISABLE_MONITORING"

            else:
                logger.warning("No audio content")

            if self.state == "START":
                text_to_say = self._generate_response_text("ASK_ROADS")
                self.state = "ASK_ROADS"
            else:
                text_to_say = self._generate_response_text(
                    self.state, self.extracted_road
                )

            logger.info(f"[TYMON]: {text_to_say}")

            audio_base64 = self._generate_audio(text_to_say)

            response = verify_answer(self.name, {"audio": audio_base64})
            # STOP IF FLAG IS FOUND
            if "FLG" in response.get("message", ""):
                return response

        logger.warning("Max iterations reached")
        return response
