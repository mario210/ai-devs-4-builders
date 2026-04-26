from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class PowerPlantAgent(BaseTask):
    """
    An agent responsible for requesting the status of power plants.
    It interacts with an external verification service to initiate the retrieval
    of power plant status information. The actual results will be polled by another agent.
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the PowerPlantAgent.

        Args:
            agent_model: The underlying agent model.
            memory: The memory object for storing and retrieving data.
        """
        super().__init__(agent=agent_model, memory=memory, name="PowerPlantAgent")

    def execute(self):
        """
        Executes the logic to request power plant status data.
        It retrieves the current task name from memory and then calls the
        `verify_answer` tool to request power plant status information.
        The actual retrieval of the result is handled by the ResultsPollingAgent.
        """
        # Retrieve the current task name from memory.
        task_name = self.memory.get("task_name")
        # Send a request to the hub to get power plant status data.
        # This initiates an asynchronous operation; the result will be polled later.
        verify_answer(task_name, {"action": "get", "param": "powerplantcheck"})
