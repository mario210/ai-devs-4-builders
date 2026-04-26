import logging
from ai.task import BaseTask
from ai.memory import SharedMemory
from data_loader import DataLoader
from city_matcher import CityMatcher
from order_service import OrderService

logger = logging.getLogger(__name__)


class FoodWarehouseTask(BaseTask):
    """Orchestrator for the FoodWarehouseTask."""

    def __init__(self, agent, memory: SharedMemory):
        super().__init__(memory.get("task_name"), agent, memory)

    def execute(self):
        logger.info("Executing FoodWarehouseTask (modular architecture)")

        # Initialize modules
        loader = DataLoader(self.name)
        city_needs = loader.load_city_needs()
        destinations = loader.load_destinations()
        users = loader.load_users()
        matcher = CityMatcher(
            self.agent, {d["name"].lower(): d["destination_id"] for d in destinations}
        )
        orders = OrderService(self.name)

        # Find transport user
        creator = next(
            (u for u in users if u.get("is_active") == 1 and u.get("role") == 2), None
        )
        if not creator:
            return logger.error("No valid transport user found.")

        # Reset task
        orders.reset()

        # Process cities
        for city_name, required_items in city_needs.items():
            destination_code = matcher.match(city_name)
            if not destination_code:
                continue

            signature = orders.generate_signature(
                creator["login"], creator["birthday"], destination_code
            )
            if not signature:
                continue

            order_id = orders.create_order(
                f"Dostawa dla {city_name}",
                creator["user_id"],
                destination_code,
                signature,
            )
            if not order_id:
                continue

            if required_items:
                orders.append_items(order_id, required_items)

            logger.info(f"Order {order_id} completed for {city_name}")

        # Finalize
        orders.done()
