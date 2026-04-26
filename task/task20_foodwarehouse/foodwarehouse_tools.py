import logging
import os
from dotenv import load_dotenv
import requests
from typing import Dict, Any, List, Optional
from ai.tools.hub_requests import verify_answer

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
FOOD_4_CITIES_URL = os.environ.get("HUB_DANE_BASE_URL") + "/food4cities.json"


class FoodWarehouseTools:
    """A toolkit of functions for the FoodWarehouse agent."""

    def __init__(self, task_name: str):
        self.task_name = task_name

    def _request(self, tool_name: str, action: str = None, **kwargs) -> Dict[str, Any]:
        payload = {"tool": tool_name}
        if action:
            payload["action"] = action
        payload.update(kwargs)
        return verify_answer(self.task_name, payload)

    # --- Task State Tools ---
    def reset_task_state(self) -> Dict[str, Any]:
        """Resets the remote task state. Should be called once at the beginning."""
        logger.info("TOOL: Resetting task state.")
        return self._request("reset")

    def finalize_task(self) -> Dict[str, Any]:
        """Finalizes the task. Should be called once at the very end after all orders are processed."""
        logger.info("TOOL: Finalizing task.")
        return self._request("done")

    # --- Data Loading Tools ---
    def get_city_needs(self) -> Dict[str, Any]:
        """Fetches a list of cities and their required food items from an external source."""
        logger.info("TOOL: Fetching city needs.")
        try:
            resp = requests.get(FOOD_4_CITIES_URL)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to load city needs: {e}")
            return {"error": str(e)}

    def get_destinations(self) -> List[Dict[str, Any]]:
        """Fetches all available delivery destinations from the database."""
        logger.info("TOOL: Fetching destinations.")
        all_rows, limit, offset = [], 50, 0
        while True:
            response = verify_answer(
                self.task_name,
                {
                    "tool": "database",
                    "query": f"select * from destinations limit {limit} offset {offset}",
                },
            )
            rows = response.get("rows", [])
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < limit:
                break
            offset += limit
        return all_rows

    def get_users(self) -> List[Dict[str, Any]]:
        """Fetches all users from the database."""
        logger.info("TOOL: Fetching users.")
        response = verify_answer(
            self.task_name, {"tool": "database", "query": "select * from users"}
        )
        return response.get("rows", [])

    # --- Order Processing Tools ---
    def generate_order_signature(
        self, login: str, birthday: str, destination_id: int
    ) -> Optional[str]:
        """Generates a cryptographic signature required for creating an order."""
        logger.info(f"TOOL: Generating signature for {login} to {destination_id}.")
        resp = self._request(
            "signatureGenerator",
            action="generate",
            login=login,
            birthday=birthday,
            destination=destination_id,
        )
        return resp.get("hash")

    def create_delivery_order(
        self, title: str, creator_id: int, destination_id: int, signature: str
    ) -> Optional[int]:
        """Creates a new delivery order and returns the order ID."""
        logger.info(f"TOOL: Creating order '{title}'.")
        resp = self._request(
            "orders",
            action="create",
            title=title,
            creatorID=creator_id,
            destination=destination_id,
            signature=signature,
        )
        order_id = (
            resp.get("order", {}).get("id")
            or resp.get("id")
            or resp.get("answer", {}).get("id")
        )
        if order_id:
            logger.info(f"Successfully created order with ID: {order_id}")
        else:
            logger.error(f"Failed to create order. Response: {resp}")
        return order_id

    def add_items_to_order(self, order_id: int, items: Dict[str, Any]):
        """Appends a list of items (name and quantity) to an existing order."""
        logger.info(f"TOOL: Adding {len(items)} item types to order {order_id}.")
        return self._request("orders", action="append", id=order_id, items=items)
