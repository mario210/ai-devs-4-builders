import os
from dotenv import load_dotenv
from ai.agent import AGENTS_API_KEY
from ai.tools.hub_requests import post_json_request

# Load environment variables
load_dotenv()

PACKAGES_API_URL = os.environ.get("HUB_API_PACKAGES_URL")


# --- Tool Functions ---
def check_package(package_id):
    """Checks package status."""
    payload = {"apikey": AGENTS_API_KEY, "action": "check", "packageid": package_id}
    return post_json_request(payload, url=PACKAGES_API_URL)


def redirect_package(package_id, destination, code):
    """Redirects package."""
    payload = {
        "apikey": AGENTS_API_KEY,
        "action": "redirect",
        "packageid": package_id,
        "destination": destination,
        "code": code,
    }
    return post_json_request(payload, url=PACKAGES_API_URL)


PACKAGE_OPERATIONS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_package",
            "description": "Check the status and location of a package given its ID.",
            "parameters": {
                "type": "object",
                "properties": {"package_id": {"type": "string"}},
                "required": ["package_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "redirect_package",
            "description": "Redirect a package to a new destination using a security code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_id": {"type": "string"},
                    "destination": {"type": "string"},
                    "code": {"type": "string"},
                },
                "required": ["package_id", "destination", "code"],
            },
        },
    },
]

PACKAGE_OPERATIONS_TOOLS_MAP = {
    "check_package": check_package,
    "redirect_package": redirect_package,
}
