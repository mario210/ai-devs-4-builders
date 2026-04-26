from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class WeatherAgent(BaseTask):
    """
    An agent responsible for requesting weather forecast data.
    It interacts with the external verification service to initiate a weather data retrieval.
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the WeatherAgent.

        Args:
            agent_model: The underlying agent model.
            memory: The memory object for storing and retrieving data.
        """
        super().__init__(agent=agent_model, memory=memory, name="WeatherAgent")

    def execute(self):
        """
        Executes the weather data request logic.
        It retrieves the task name from memory and then calls the `verify_answer`
        tool to request weather information. The actual retrieval of the result
        is handled by the ResultsPollingAgent.
        """
        # Retrieve the current task name from memory.
        task_name = self.memory.get("task_name")
        # Send a request to the hub to get weather data.
        # This initiates an asynchronous operation; the result will be polled later.
        verify_answer(task_name, {"action": "get", "param": "weather"})
