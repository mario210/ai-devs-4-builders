import logging
import os
from dotenv import load_dotenv
import requests
from typing import Dict, Any, List
from ai.tools.hub_requests import verify_answer

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
FOOD_4_CITIES_URL = os.environ.get("HUB_DANE_BASE_URL") + "/food4cities.json"


class DataLoader:
    """Loads city needs, destinations, and users from external sources."""

    def __init__(self, task_name: str):
        self.task_name = task_name

    def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return verify_answer(self.task_name, payload)

    @staticmethod
    def load_city_needs() -> Dict[str, Any]:
        try:
            resp = requests.get(FOOD_4_CITIES_URL)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to load city needs: {e}")
            return {}

    def load_destinations(self) -> List[Dict[str, Any]]:
        all_rows, limit, offset = [], 30, 0
        while True:
            response = self._request(
                {
                    "tool": "database",
                    "query": f"select * from destinations limit {limit} offset {offset}",
                }
            )
            rows = response.get("rows", [])
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < limit:
                break
            offset += limit
        logger.info(f"Loaded {len(all_rows)} destinations")
        return all_rows

    def load_users(self) -> List[Dict[str, Any]]:
        response = self._request({"tool": "database", "query": "select * from users"})
        return response.get("rows", [])
