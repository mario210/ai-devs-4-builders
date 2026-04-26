from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class DocumentationAgent(BaseTask):
    """
    An agent responsible for fetching and parsing the wind turbine documentation.
    It retrieves critical operational parameters like rated power, wind yield table,
    and safety rules (max/min operational wind speeds) from the documentation
    and stores them in memory for other agents to use.
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the DocumentationAgent.

        Args:
            agent_model: The underlying agent model.
            memory: The memory object for storing and retrieving data.
        """
        super().__init__(agent=agent_model, memory=memory, name="DocumentationAgent")

    def execute(self):
        """
        Executes the logic to fetch and process documentation.

        It requests the documentation from the external service, validates the response,
        extracts key operational parameters, and stores them in the agent's memory.
        Raises ValueError if documentation fetching fails or critical data is missing.
        """
        # Retrieve the current task name from memory.
        doc_response = verify_answer(
            self.memory.get("task_name"), {"action": "get", "param": "documentation"}
        )

        # Check if the documentation request was successful.
        if doc_response.get("code") != 50:
            raise ValueError(f"Failed to get documentation. Response: {doc_response}")

        # Store the raw documentation response in memory.
        doc_data = doc_response
        self.memory.set("documentation", doc_data)

        # Extract specific critical parameters from the documentation.
        rated_power = doc_data.get("ratedPowerKw")
        wind_yield_table = doc_data.get("windPowerYieldPercent")
        safety_rules = doc_data.get("safety", {})
        max_wind_speed = safety_rules.get("cutoffWindMs")
        min_operational_wind_ms = safety_rules.get("minOperationalWindMs")

        # Validate that all critical documentation data has been successfully extracted.
        if not all(
            [
                rated_power,
                wind_yield_table,
                max_wind_speed is not None,
                min_operational_wind_ms is not None,
            ]
        ):
            raise ValueError(f"Missing critical documentation data. Got: {doc_data}")

        # Store the extracted critical parameters individually in memory for easy access.
        self.memory.set("rated_power", rated_power)
        self.memory.set("wind_yield_table", wind_yield_table)
        self.memory.set("max_wind_speed", max_wind_speed)
        self.memory.set("min_operational_wind_ms", min_operational_wind_ms)
