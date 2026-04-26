import logging
from typing import Dict, Any, Optional
from ai.tools.hub_requests import verify_answer

logger = logging.getLogger(__name__)


class OrderService:
    """Handles signature generation and order creation."""

    def __init__(self, task_name: str):
        self.task_name = task_name

    def _request(self, tool_name: str, action: str = None, **kwargs) -> Dict[str, Any]:
        payload = {"tool": tool_name}
        if action:
            payload["action"] = action
        payload.update(kwargs)
        return verify_answer(self.task_name, payload)

    def reset(self) -> Dict[str, Any]:
        return self._request("reset")

    def done(self) -> Dict[str, Any]:
        return self._request("done")

    def generate_signature(
        self, login: str, birthday: str, destination: int
    ) -> Optional[str]:
        resp = self._request(
            "signatureGenerator",
            action="generate",
            login=login,
            birthday=birthday,
            destination=destination,
        )
        return resp.get("hash")

    def create_order(
        self, title: str, creator_id: int, destination: int, signature: str
    ) -> Optional[int]:
        resp = self._request(
            "orders",
            action="create",
            title=title,
            creatorID=creator_id,
            destination=destination,
            signature=signature,
        )
        return (
            resp.get("order", {}).get("id")
            or resp.get("id")
            or resp.get("answer", {}).get("id")
        )

    def append_items(self, order_id: int, items: Dict[str, Any]):
        self._request("orders", action="append", id=order_id, items=items)
