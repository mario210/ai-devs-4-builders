import time
from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class ResultsPollingAgent(BaseTask):
    """
    An agent responsible for continuously polling for results from various
    asynchronous operations until all expected results are received or a timeout occurs.
    It processes different types of results (e.g., weather forecast, powerplant status,
    turbine status, unlock codes) and stores them in memory.
    """

    def __init__(self, agent_model, memory):
        super().__init__(agent=agent_model, memory=memory, name="ResultsPollingAgent")

    def execute(self):
        """
        Executes the polling logic. It repeatedly calls `verify_answer` to check for
        new results, processes them based on their source function, and updates
        the count of expected results. It includes a timeout mechanism.
        """
        # Retrieve the task name and the dictionary of expected results counts from memory.
        # expected_results_count maps source function names to the number of results still awaited.
        task_name = self.memory.get("task_name")
        expected_results = self.memory.get("expected_results_count")

        start_time = time.time()
        # Continue polling as long as there's at least one type of result still expected (count > 0).
        while any(count > 0 for count in expected_results.values()):
            # Check for timeout. If more than 35 seconds have passed, raise an error.
            if time.time() - start_time > 35:
                # Identify which results are still missing.
                missing = {k: v for k, v in expected_results.items() if v > 0}
                raise TimeoutError(f"Failed to get all results. Missing: {missing}")

            # Call the external verification service to get new results.
            response = verify_answer(task_name, {"action": "getResult"})

            # If the response is not a dictionary or indicates no new results (code 11),
            # wait a bit and try again.
            if not isinstance(response, dict) or response.get("code") == 11:
                time.sleep(0.2)
                continue

            # Extract the source function from the response to determine its type.
            source_function = response.get("sourceFunction")

            # Process results based on their source function.
            # For each type, if results are still expected, store the response in memory
            # and decrement the count of expected results for that type.
            if source_function == "weather" and expected_results["forecast"] > 0:
                self.memory.set("forecast", response)
                expected_results["forecast"] -= 1
            elif (
                source_function == "powerplantcheck"
                and expected_results["powerplant"] > 0
            ):
                self.memory.set("powerplant", response)
                expected_results["powerplant"] -= 1
            elif (
                source_function == "turbinecheck"
                and expected_results["turbine_status"] > 0
            ):
                self.memory.set("turbine_status", response)
                expected_results["turbine_status"] -= 1
            elif (
                source_function == "unlockCodeGenerator"
                and expected_results["unlockCodeGenerator"] > 0
            ):
                # For unlock codes, extract the code and signed parameters.
                unlock_code = response["unlockCode"]
                signed_params = response["signedParams"]
                # Create a unique key for the unlock code based on its start date and hour.
                signed_date_str = (
                    f"{signed_params['startDate']} {signed_params['startHour']}"
                )

                # Retrieve the existing map of unlock codes or initialize it if not present.
                unlock_codes = self.memory.get("unlockCodeGenerator_map")
                if unlock_codes is None:
                    unlock_codes = {}
                unlock_codes[signed_date_str] = unlock_code
                self.memory.set("unlockCodeGenerator_map", unlock_codes)
                expected_results["unlockCodeGenerator"] -= 1

            # After processing a result, update the overall expected results count in memory.
            self.memory.set("expected_results_count", expected_results)
            time.sleep(0.2)
