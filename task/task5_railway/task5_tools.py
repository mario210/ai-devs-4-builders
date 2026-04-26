import os
from dotenv import load_dotenv
from ai.agent import AGENTS_API_KEY
from ai.tools.hub_requests import post_json_request

# Load environment variables
load_dotenv()

VERIFY_API_URL = os.environ.get("HUB_API_VERIFY_URL")


def get_railway_instructions():
    """Fetches the railway task instructions."""
    payload = {
        "apikey": AGENTS_API_KEY,
        "task": "railway",
        "answer": {"action": "help"},
    }
    return post_json_request(payload, url=VERIFY_API_URL)


def submit_railway_answer(answer):
    """Sends a generic answer/command to the railway task."""
    payload = {"apikey": AGENTS_API_KEY, "task": "railway", "answer": answer}
    return post_json_request(payload, url=VERIFY_API_URL)


RAILWAY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_railway_instructions",
            "description": "Fetches the railway task instructions (action=help).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_railway_answer",
            "description": "Sends a command/answer to the railway system. Use this to execute actions found in documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "object",
                        "description": "The JSON object containing the action and parameters required by the railway API (e.g. {'action': '...', ...}).",
                    }
                },
                "required": ["answer"],
            },
        },
    },
]

RAILWAY_TOOLS_MAP = {
    "get_railway_instructions": get_railway_instructions,
    "submit_railway_answer": submit_railway_answer,
}
