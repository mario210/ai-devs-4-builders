import time
import os
from dotenv import load_dotenv

import requests
import re
from rapidfuzz import fuzz
from loguru import logger

from ai.tools.hub_requests import retry_verify_answer

# Load environment variables
load_dotenv()

HUB_BASE_URL = os.environ.get("HUB_API_BASE_URL")


class RocketControlAgent:
    def __init__(self, base_url, api_key, agent_model):
        self.base_url = base_url
        self.api_key = api_key
        self.agent_model = agent_model

    def start_game(self):
        return self._send_command("start")

    def make_move(self, move):
        return self._send_command(move)

    def _send_command(self, command):
        verification_response = retry_verify_answer("goingthere", {"command": command})

        if verification_response.get("code") < 0 and verification_response.get(
            "crashReason"
        ):
            error_message = (
                f"The rocket crashed. Reason {verification_response.get("crashReason")}"
            )
            logger.error(error_message)
            return {"error": error_message}

        return verification_response

    def decide_move(self, hint, current_position):
        current_row, current_col = current_position
        rock_row = hint.get("rock", {}).get("row")

        if rock_row is None:
            return "go"

        # Adjust rock_row to be 0-indexed for comparison
        rock_row -= 1

        # Determine safe rows
        safe_rows = [0, 1, 2]
        if rock_row in safe_rows:
            safe_rows.remove(rock_row)

        # If current row is safe, stay
        if current_row in safe_rows:
            return "go"

        # Try to move to a safe row
        for safe_r in safe_rows:
            if safe_r == current_row - 1:
                return "left"
            if safe_r == current_row + 1:
                return "right"

        return "go"


class TrapScannerAgent:
    def __init__(self, base_url, api_key, agent_model):
        self.base_url = base_url
        self.api_key = api_key
        self.agent_model = agent_model

    @staticmethod
    def _is_clear(text: str) -> bool:
        normalized = re.sub(r"[^a-z\s]", "", text.lower())

        # quick check
        if (
            "clear" in normalized
            or "cleeeeeeeear" in normalized
            or "cleeeear" in normalized
            or "cleeeeeeear" in normalized
        ):
            return True

        # fallback fuzzy
        return fuzz.partial_ratio("clear", normalized) > 75

    def get_trap_details(self):
        frequency_scanner_url = os.environ.get("HUB_API_FREQUENCY_SCANNER_URL")
        url = f"{frequency_scanner_url}?key={self.api_key}"  # Corrected URL
        for attempt in range(10):  # Using a fixed retry count
            try:
                response = requests.get(url)
                response.raise_for_status()
                text = response.text
                if not self._is_clear(text):
                    logger.warning(f"Trap detected: {text}")
                    return text
                return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt+1}: Error checking for traps: {e}")
                time.sleep(2**attempt)
        return None

    def disarm_with_data(self, frequency, detection_code):
        import hashlib
        import time
        import requests

        string_to_hash = detection_code + "disarm"
        disarm_hash = hashlib.sha1(string_to_hash.encode()).hexdigest()

        payload = {
            "apikey": self.api_key,
            "frequency": frequency,
            "disarmHash": disarm_hash,
        }

        frequency_scanner_url = os.environ.get("HUB_API_FREQUENCY_SCANNER_URL")
        url = frequency_scanner_url

        for attempt in range(10):
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
                logger.success("Trap disarmed")
                return True
            except Exception as e:
                logger.error(f"Disarm error {attempt + 1}: {e}")
                time.sleep(2**attempt)

        return False


class RadioHintAgent:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def get_hint(self):
        get_message_url = os.environ.get("HUB_API_GET_MESSAGE_URL")
        url = get_message_url  # Corrected URL
        payload = {"apikey": self.api_key}
        for attempt in range(10):
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt+1}: Error getting hint: {e}")
                time.sleep(2**attempt)
        return None
