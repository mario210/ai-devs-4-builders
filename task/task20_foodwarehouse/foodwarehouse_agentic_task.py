import logging
from ai.task import BaseTask
from ai.memory import SharedMemory
from foodwarehouse_tools import FoodWarehouseTools

logger = logging.getLogger(__name__)


class FoodWarehouseAgenticTask(BaseTask):
    """Orchestrator for the FoodWarehouseTask using an agentic approach."""

    def __init__(self, agent, memory: SharedMemory):
        super().__init__(memory.get("task_name"), agent, memory)

    def execute(self):
        logger.info("Executing FoodWarehouseTask (Agentic Architecture)")

        tools_manager = FoodWarehouseTools(self.name)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "reset_task_state",
                    "description": "Resets the remote task state. Should be called once at the beginning.",
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "finalize_task",
                    "description": "Finalizes the task. Should be called once at the very end after all orders are processed.",
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_city_needs",
                    "description": "Fetches a list of cities and their required food items.",
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_destinations",
                    "description": "Fetches all available delivery destinations from the database.",
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_users",
                    "description": "Fetches all users from the database.",
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_order_signature",
                    "description": "Generates a cryptographic signature required for creating an order.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "login": {"type": "string"},
                            "birthday": {"type": "string"},
                            "destination_id": {"type": "integer"},
                        },
                        "required": ["login", "birthday", "destination_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_delivery_order",
                    "description": "Creates a new delivery order and returns the order ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "creator_id": {"type": "integer"},
                            "destination_id": {"type": "integer"},
                            "signature": {"type": "string"},
                        },
                        "required": [
                            "title",
                            "creator_id",
                            "destination_id",
                            "signature",
                        ],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_items_to_order",
                    "description": "Appends a list of items (name and quantity) to an existing order.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "integer"},
                            "items": {"type": "object"},
                        },
                        "required": ["order_id", "items"],
                    },
                },
            },
        ]

        tool_map = {
            "reset_task_state": tools_manager.reset_task_state,
            "finalize_task": tools_manager.finalize_task,
            "get_city_needs": tools_manager.get_city_needs,
            "get_destinations": tools_manager.get_destinations,
            "get_users": tools_manager.get_users,
            "generate_order_signature": tools_manager.generate_order_signature,
            "create_delivery_order": tools_manager.create_delivery_order,
            "add_items_to_order": tools_manager.add_items_to_order,
        }

        prompt = """
        You are a logistics manager for a food warehouse. Your goal is to process all food delivery orders.
        Follow these steps precisely and methodically. Do not skip any steps.

        1.  **Begin**: Call `reset_task_state` to start with a clean slate.
        2.  **Gather Data**:
            - Call `get_city_needs` to get the list of orders.
            - Call `get_destinations` to get all possible delivery locations.
            - Call `get_users` to get all user data.
        3.  **Identify Creator**: From the user data, find the single user who is both active (`is_active` == 1) and has the role of a transport creator (`role` == 2). You will need their `login`, `birthday`, and `user_id` for all subsequent order creations.
        4.  **Process Each City**: Iterate through each city from the city needs list. For each city:
            a. **Match Destination**: Find the corresponding destination in the destinations list by matching the city name. The match must be exact but case-insensitive. Store its `destination_id`. If you cannot find an exact match, you must skip this city and move to the next one.
            b. **Generate Signature**: Call `generate_order_signature` using the creator's `login`, `birthday`, and the `destination_id` you just found.
            c. **Create Order**: Call `create_delivery_order`. Use a descriptive title like "Dostawa dla [City Name]", the creator's `user_id`, the `destination_id`, and the signature from the previous step.
            d. **Add Items**: If the order was created successfully and returned an `order_id`, call `add_items_to_order` with that `order_id` and the required items for that city.
        5.  **Finalize**: After you have processed every city in the needs list, call `finalize_task` to complete the job.

        Now, begin the process by resetting the task state.
        """

        logger.info("Handing control to the agent...")
        self.agent.chat(
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_map=tool_map,
            max_iterations=50,  # Allow enough iterations for all cities
        )
        logger.info("Agent has completed its work.")
