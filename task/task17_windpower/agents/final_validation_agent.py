from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class FinalValidationAgent(BaseTask):
    """
    An agent responsible for performing final validation checks and signaling
    the completion of the task to the external service.

    It checks the turbine status and then sends a 'done' action.
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the FinalValidationAgent.

        Args:
            agent_model: The underlying agent model.
            memory: The memory object for storing and retrieving data.
        """
        super().__init__(agent=agent_model, memory=memory, name="FinalValidationAgent")

    def execute(self):
        """
        Executes the final validation and completion logic.

        It retrieves the turbine status from memory, verifies it's operating correctly.
        If the turbine status is not as expected, it raises a RuntimeError.
        Finally, it sends a 'done' action to the external service.
        """
        # Retrieve the current task name from memory.
        task_name = self.memory.get("task_name")
        # Retrieve the turbine status obtained by the ResultsPollingAgent.
        turbine_status = self.memory.get("turbine_status")

        # Perform a critical check: ensure the turbine is operating correctly.
        if not (
            turbine_status
            and turbine_status.get("status") == "Turbine is operating correctly."
        ):
            raise RuntimeError(f"Turbine check failed: {turbine_status}")

        # If all checks pass, signal task completion to the external service.
        final_response = verify_answer(task_name, {"action": "done"})
        print(f"Final response: {final_response}")
