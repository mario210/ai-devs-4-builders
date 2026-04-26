from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class EvacuationAgent(BaseTask):
    """
    The EvacuationAgent is responsible for the final stage of the rescue mission:
    planning and executing the extraction of the target (partisan) once located.
    It interacts with the central hub to call for an evacuation vehicle (e.g., helicopter).
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the EvacuationAgent.

        Args:
            agent_model: The underlying AI model used by the agent for decision-making.
            memory: The shared memory object where agents store and retrieve information.
        """
        self.name = "EvacuationAgent"
        self.agent_model = agent_model
        self.memory = memory

    def execute(self):
        """
        Executes the evacuation logic.
        It checks if the partisan has been found and, if so, attempts to call for evacuation
        using the coordinates stored in shared memory.
        """
        task_name = self.memory.get("task_name")

        if self.memory.get("partisan_found"):
            coordinates = self.memory.get("partisan_coordinates")
            if coordinates:
                print(
                    f"Partisan found at {coordinates}. Calling helicopter for evacuation."
                )
                # Call the central hub API to request a helicopter for evacuation
                verify_answer(
                    task_name, {"action": "callHelicopter", "destination": coordinates}
                )
                print(f"Mission successful.")
            else:
                print(
                    "Error: Partisan found, but coordinates were not provided by FieldCommanderAgent."
                )
        else:
            print(f"Mission failed. Partisan was not found.")
