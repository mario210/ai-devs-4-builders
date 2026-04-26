import os
from dotenv import load_dotenv
from ai.agent import AGENTS_API_KEY
from ai.tools.hub_requests import post_json_request

# Load environment variables
load_dotenv()

VERIFY_API_URL = os.environ.get("HUB_API_VERIFY_URL")


def submit_categorization(answer):
    """Submits the categorization results."""
    payload = {"apikey": AGENTS_API_KEY, "task": "categorize", "answer": answer}
    return post_json_request(payload, url=VERIFY_API_URL)


SUBMIT_CATEGORIZATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "submit_categorization",
            "description": "Submits the categorization results to the hub.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "object",
                        "description": "A JSON object mapping item IDs to their categories (DNG/NEU).",
                    }
                },
                "required": ["answer"],
            },
        },
    }
]

SUBMIT_CATEGORIZATION_TOOLS_MAP = {"submit_categorization": submit_categorization}
