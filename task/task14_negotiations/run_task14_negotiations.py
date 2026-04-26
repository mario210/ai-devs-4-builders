import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ai.tools.hub_requests import verify_answer
import time

NGROK_URL = "https://f564-109-206-219-14.ngrok-free.app"
tools_desc_payload = {
    "tools": [
        {
            "URL": f"{NGROK_URL}/find_cities_for_item",
            "description": (
                "Finds cities that offer a specific item. Provide the item name as a string in `params`. "
                "The server will attempt to match your description to a known item. "
                'E.g., `{"params": "Akumulator 48V"}` or `{"params": "Turbina wiatrowa 400W"}`.'
            ),
        }
    ]
}

if __name__ == "__main__":
    print("\n--- Running Task 14: Negotiations ---")
    verify_answer("negotiations", tools_desc_payload)

    for i in range(20):
        print(f"Sending verification request {i+1}/20...")
        res = verify_answer("negotiations", {"action": "check"})
        msg = res.get("message", "")
        if isinstance(msg, str) and "flg" in msg.lower():
            break
        time.sleep(11)
