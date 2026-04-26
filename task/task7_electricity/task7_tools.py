import json
import os
from dotenv import load_dotenv
from ai.agent import AGENTS_API_KEY
import requests

load_dotenv()

VERIFY_API_URL = os.environ.get("HUB_API_VERIFY_URL")


def submit_electricity_answer(rotate: str):
    """
    Submits an answer for the electricity puzzle.
    :param rotate: The coordinates of the square to rotate, e.g., '2x3'.
    """
    print(f"Submitting rotation for coordinates: {rotate}")
    url = VERIFY_API_URL
    payload = {
        "apikey": AGENTS_API_KEY,
        "task": "electricity",
        "answer": {"rotate": rotate},
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"API Response: {result}")
        return result
    except requests.RequestException as e:
        error_message = f"HTTP Request failed: {e}"
        print(error_message)
        return {"error": error_message}
    except json.JSONDecodeError:
        error_message = f"Failed to decode JSON from response: {response.text}"
        print(error_message)
        return {"error": error_message}


SUBMIT_ANSWER_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "submit_electricity_answer",
            "description": "Submits a coordinate to rotate for the electricity puzzle. Example: '1x1', '2x3'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rotate": {
                        "type": "string",
                        "description": "The coordinates of the square to rotate, e.g., '1x1', '2x3'.",
                    }
                },
                "required": ["rotate"],
            },
        },
    }
]

SUBMIT_ANSWER_TOOL_MAP = {"submit_electricity_answer": submit_electricity_answer}
