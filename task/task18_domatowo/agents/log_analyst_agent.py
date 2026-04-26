from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer
import json


class LogAnalystAgent(BaseTask):
    """
    The LogAnalystAgent is responsible for retrieving and analyzing system logs
    to find critical information, specifically the location of the missing partisan.
    It uses an LLM to interpret log entries and extract structured data.
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the LogAnalystAgent.

        Args:
            agent_model: The underlying AI model used by the agent for analysis.
            memory: The shared memory object where agents store and retrieve information.
        """
        super().__init__(agent=agent_model, memory=memory, name="LogAnalystAgent")
        self.memory = memory
        self.task_name = self.memory.get("task_name")

    def execute(self, current_tile=None):
        """
        Executes the log analysis process.

        1. Requests logs from the central hub.
        2. Parses the log response.
        3. Constructs a prompt for the LLM to analyze the log content.
        4. Calls the LLM to identify if a partisan was found and their coordinates.
        5. Updates shared memory if the partisan's location is successfully identified.
        Returns:
            bool: True if the partisan's coordinates were found and set in memory, False otherwise.
        """
        log_payload = {"action": "getLogs"}
        print("LogAnalystAgent: Checking logs for partisan...")
        logs_response = verify_answer(self.task_name, log_payload)
        print(f"LogAnalystAgent: GetLogs response: {logs_response}")

        # Handle the structure where the actual list of log objects is in the "logs" key
        # This ensures we're working with the actual log entries.
        if logs_response and "logs" in logs_response:
            log_content = json.dumps(logs_response["logs"], ensure_ascii=False)

            # Construct a detailed prompt for the LLM to analyze the log content.
            # The prompt explicitly asks for a JSON output format.
            prompt = f"""Analyze the following JSON logs to determine if a survivor, partisan, or human target was found based on the 'msg' field.
If someone was found, extract the value of the 'field' key associated with that specific message. This value represents their current coordinates.

Respond ONLY with a valid JSON object in the following format (no markdown, no extra text):
{{
    "found": true or false,
    "coordinates": "x,y" or null
}}

Logs to analyze:
{log_content}
"""
            # Send the prompt to the agent's LLM for analysis.
            response = self.agent.chat(messages=[{"role": "user", "content": prompt}])
            print(f"LogAnalystAgent: LLM analysis response: {response}")

            try:
                # Clean up the LLM's response in case it includes markdown formatting (e.g., ```json).
                # This ensures that json.loads can parse it correctly.
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:-3].strip()
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:-3].strip()

                # Attempt to parse the cleaned response as a JSON object.
                result = json.loads(cleaned_response)

                # If the LLM determined a partisan was found, extract their coordinates
                # and update the shared memory for other agents.
                if result.get("found"):
                    coordinates = result.get("coordinates")
                    print(
                        f"LogAnalystAgent: Partisan found! Destination coordinates: {coordinates}. Reporting to Orchestrator."
                    )
                    self.memory.set("partisan_found", True)
                    self.memory.set("partisan_coordinates", coordinates)
                    return True
            except json.JSONDecodeError:
                # Handle cases where the LLM's response is not valid JSON.
                print("LogAnalystAgent: Failed to parse LLM response as JSON.")

        return False
