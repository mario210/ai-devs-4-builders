import base64
import json
import os
import tempfile
import requests
from typing import Optional
from ai.task import BaseTask
from ai.memory import SharedMemory
from ai.agent import Agent
from ai.tools.hub_requests import verify_answer
from dotenv import load_dotenv

load_dotenv()


class RadiomonitoringListenerTask(BaseTask):
    def __init__(self, agent: Agent, memory: SharedMemory):
        super().__init__(name="Radiomonitoring Listener", agent=agent, memory=memory)

    def execute(self) -> None:
        task_name = self.memory.get("task_name")
        print(f"Executing {self.name} for task {task_name}")

        useful_data = []

        while True:
            response = verify_answer(task_name, {"action": "listen"})
            print(f"Received response: {response}")

            if isinstance(response, dict):
                message = response.get("message", "")
                transcription = response.get("transcription")
                attachment = response.get("attachment")

                # 1. ROZPOZNAWANIE MATERIAŁU I ROUTING
                if transcription:
                    # Tekst - analizujemy kodem (lokalnie, darmowo)
                    if self._is_useful_text_local(transcription):
                        useful_data.append({"type": "text", "content": transcription})
                        print(f"Captured useful text: {transcription}")
                    else:
                        print(f"Ignored noise in text: {transcription}")

                elif attachment:
                    # Binarka - programistyczny router decyduje co z tym zrobić
                    attachment_meta = response.get("meta", "")
                    filesize = response.get("filesize", 0)

                    useful_content = self._route_and_process_attachment(
                        attachment, attachment_meta, filesize
                    )

                    if useful_content:
                        useful_data.append(
                            {
                                "type": "attachment",
                                "meta": attachment_meta,
                                "content": useful_content,
                                "filesize": filesize,
                            }
                        )
                        print(f"Captured useful attachment of type {attachment_meta}")
                    else:
                        print(
                            f"Ignored noise or unreadable data in attachment type {attachment_meta}."
                        )

                # 2. CZEKAMY NA SYGNAŁ Z SYSTEMU (zamiast sprawdzać LLM-em w pętli)
                # "Gdy materiał się skończy, system poinformuje Cię..."
                if (
                    "wystarczająco" in message.lower()
                    or "komplet" in message.lower()
                    or "done" in message.lower()
                    or "zakończ" in message.lower()
                    or "analiz" in message.lower()
                ):
                    print(
                        "API indicated enough data collected (wystarczająco dużo danych)."
                    )
                    break
            else:
                print(
                    f"Unexpected response type: {type(response)}. Content: {response}"
                )
                break

        # Zapisz zebrane dane na wypadek gdybyśmy chcieli je podejrzeć
        self.memory.set("radio_transcriptions", useful_data)
        print(f"Total useful data pieces captured: {len(useful_data)}")

        self._save_collected_data_to_file(useful_data)

        # 3. KIEROWANIE DO MODELU: Dopiero na samym końcu uruchamiamy drogi model do analizy
        print("Extracting final findings from collected data using LLM...")
        extracted_info = self._extract_final_information(useful_data)
        if extracted_info:
            print(f"Final extraction success: {extracted_info}")
            self.memory.set("radio_findings", extracted_info)
        else:
            print("Failed to extract full information.")

    def _save_collected_data_to_file(
        self, data: list, filename: str = "collected_radio_data.txt"
    ) -> None:
        """Saves all collected useful strings into a text file for debugging/archiving."""
        try:
            # You can place this file anywhere you'd prefer; saving in the task directory by default.
            current_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(current_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write("--- RADIOMONITORING COLLECTED DATA ---\n\n")
                for idx, item in enumerate(data, start=1):
                    msg_type = item.get("type", "unknown")
                    content = item.get("content", "")
                    if msg_type == "text":
                        f.write(f"[{idx}] TEXT: {content}\n")
                    elif msg_type == "attachment":
                        meta = item.get("meta", "")
                        f.write(f"[{idx}] ATTACHMENT ({meta}): {content}\n")
                f.write("\n--------------------------------------\n")
            print(f"Successfully saved collected data to: {filepath}")
        except Exception as e:
            print(f"Failed to save collected data to file: {e}")

    def _extract_final_information(self, current_data: list) -> Optional[dict]:
        """Używa LLM (jeden raz na końcu!) by wyciągnąć 4 konkretne wartości."""
        data_str = ""
        for item in current_data:
            data_str += f"- {item['content']}\n"

        if not data_str:
            return None

        prompt = f"""
We are listening to radio transmissions and analyzing captured files. 
You must identify the city that the speakers refer to as "Syjon" (Syjon is their code name or nickname, you must find its REAL, actual city name).
The true city name is hidden or mentioned somewhere in the transmissions, possibly via context clues linking it to "Syjon".

Based on all the provided clues, carefully deduce:
1. `cityName` - The real, actual name of the city they are talking about (do NOT output "Syjon", find the real city).
2. `cityArea` - The exact area of the city, rounded to exactly 2 decimal places (mathematical rounding, not just truncation) in format like "12.34". You might need to calculate it if it is given in another form or as a mathematical operation.
3. `warehousesCount` - The integer number of warehouses located in the city. If the logs do not explicitly mention warehouses, calculate this by counting all unique cities listed in the miasto column of the attached CSV or structured logs, excluding only Syjon. Count each city exactly once, ignoring duplicates, whitespace, or any variations in other columns. List all these cities explicitly when verifying your count to ensure none are missed.
4. `phoneNumber` - A phone number of a contact person from the city. Note: The phone number might be spoken as words (e.g., "trzy dwa jeden..."), please convert it to a standard numerical string format if so.

Here are the useful transmissions and file contents captured so far:
{data_str}

Analyze the data and return a strict JSON object with keys:
"cityName", "cityArea", "warehousesCount", "phoneNumber". Do not return any other text outside the JSON.
"""
        answer = self.agent.chat(messages=[{"role": "user", "content": prompt}]).strip()

        try:
            if answer.startswith("```json"):
                answer = answer[7:]
            if answer.startswith("```"):
                answer = answer[3:]
            if answer.endswith("```"):
                answer = answer[:-3]

            parsed = json.loads(answer.strip())

            if "warehousesCount" in parsed:
                try:
                    parsed["warehousesCount"] = int(parsed["warehousesCount"])
                except ValueError:
                    pass

            # Handle the discovered secret path if the LLM decoded the Morse code
            if "secret_path" in parsed:
                secret_path = parsed.pop("secret_path")
                print(
                    f"\n[!] ALERT: The LLM successfully decoded a secret path: {secret_path}"
                )
                print(
                    "[!] Automatically querying the endpoint to retrieve the missing data..."
                )

                # We try sending the path as an action to the central verification system
                # Stripping the '/' so '/deeper' becomes 'deeper'
                action_name = secret_path.strip("/")
                secret_response = verify_answer(
                    self.memory.get("task_name"), {"action": action_name}
                )
                print(f"[!] Response from {secret_path}: {secret_response}")

                # Depending on what the `/deeper` endpoint returns, you may extract the count here.
                # For example, if it returns dict with the count directly:
                # if isinstance(secret_response, dict) and "message" in secret_response:
                #    parsed["warehousesCount"] = int(secret_response["message"]) # map based on actual response

            return parsed
        except json.JSONDecodeError:
            print(f"Failed to parse LLM answer as JSON. Answer was: {answer}")
            return None

    def _is_useful_text_local(self, text: str) -> bool:
        """Szybka, darmowa filtracja szumu za pomocą zwykłego Pythona."""
        if not text:
            return False

        text_lower = text.lower().strip()
        noise_keywords = [
            "szum",
            "trzask",
            "noise",
            "static",
            "beep",
            "bzz",
            "szsz",
            "piii",
            "puk",
            "pisk",
            "trzeszczenie",
        ]

        # Odrzuć jeśli to jest jeden ze znanych szumów (np "szum...")
        if text_lower in [
            "szum",
            "szum...",
            "trzaski",
            "noise",
            "szszsz...",
            "piiii...",
            "szszsz",
            "piiii",
        ]:
            return False

        # Odrzuć jeśli całe zdanie składa się tylko i wyłącznie ze słów oznaczających szum
        words = [w.strip(".,!?\"'") for w in text_lower.split()]
        if len(words) > 0 and all(
            any(kw in word for kw in noise_keywords) for word in words
        ):
            return False

        # W przeciwnym razie zakładamy że to sensowny tekst (zostanie przeanalizowany przez LLM na samym końcu)
        return True

    def _route_and_process_attachment(
        self, attachment_b64: str, meta: str, filesize: int
    ) -> Optional[str]:
        """
        Programistyczny router dla danych binarnych.
        Kieruje dane do odpowiedniego, darmowego / taniego wariantu odkodowania.
        """
        if not attachment_b64 or filesize < 50:
            return None

        try:
            decoded_bytes = base64.b64decode(attachment_b64)
            meta_lower = meta.lower()

            # 1. TEKSTOWE Binarne (JSON, XML, CSV, TXT) -> dekodujemy lokalnie, 0 kosztów!
            if any(t in meta_lower for t in ["text", "json", "xml", "csv"]):
                try:
                    text_content = decoded_bytes.decode("utf-8").strip()
                    # Filtracja lokalna, bez LLM-a!
                    if self._is_useful_text_local(text_content):
                        return text_content
                    return None
                except UnicodeDecodeError:
                    return None

            # 2. AUDIO (MP3, WAV, MPEG) -> tani model (Whisper), potem lokalna filtracja tekstu
            elif "audio" in meta_lower or "mp3" in meta_lower or "wav" in meta_lower:
                transcription = self._transcribe_audio_whisper(decoded_bytes, meta)
                if transcription and self._is_useful_text_local(transcription):
                    return f"[AUDIO TRANSCRIPT] {transcription}"
                return None

            # 3. OBRAZY (PNG, JPEG) -> model wielomodalny (Wizja)
            elif any(
                img_type in meta_lower
                for img_type in ["image/png", "image/jpeg", "image/jpg"]
            ):
                return self._describe_image_with_vision(attachment_b64, meta)

            # 4. Inne (nieznane formaty)
            else:
                print(f"Unsupported attachment meta: {meta}")
                return None

        except Exception as e:
            print(f"Router failed processing attachment: {e}")
            return None

    def _transcribe_audio_whisper(self, audio_bytes: bytes, meta: str) -> Optional[str]:
        """Tania transkrypcja za pomocą Whisper API (bez dodatkowych weryfikacji w LLM)."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        extension = "mp3" if "mpeg" in meta or "mp3" in meta else "wav"
        if "ogg" in meta:
            extension = "ogg"
        if "mp4" in meta:
            extension = "mp4"

        try:
            with tempfile.NamedTemporaryFile(
                suffix=f".{extension}", delete=False
            ) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name

            with open(temp_audio_path, "rb") as f:
                headers = {"Authorization": f"Bearer {api_key}"}
                files = {
                    "file": (f"audio.{extension}", f, meta if meta else "audio/mpeg"),
                    "model": (None, "whisper-1"),
                }
                response = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers,
                    files=files,
                )

            os.remove(temp_audio_path)

            if response.status_code == 200:
                return response.json().get("text", "").strip()
            return None
        except Exception:
            return None

    def _describe_image_with_vision(
        self, attachment_b64: str, meta: str
    ) -> Optional[str]:
        """Drogie modele wizyjne uruchamiamy tylko wtedy, gdy faktycznie mamy obraz."""
        prompt = "Przeanalizuj ten obraz i odczytaj wszelki widoczny tekst, powiedz też krótko co na nim widać. Jeśli to tylko telewizyjny szum ('śnieżenie') bez tekstu i detali, zwróć słowo 'NOISE'."
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{meta};base64,{attachment_b64}"},
                    },
                ],
            }
        ]

        answer = self.agent.chat(messages=messages)
        if not answer or "NOISE" in answer.upper():
            return None
        return answer
