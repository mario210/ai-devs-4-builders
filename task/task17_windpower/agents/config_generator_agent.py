import re
from datetime import datetime
from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


def calculate_power(
    wind_speed, rated_power, yield_table, min_operational_wind_ms, cutoff_wind_ms
):
    """
    Calculates the power output of a wind turbine given wind speed and turbine parameters.

    Args:
        wind_speed (int): Current wind speed in m/s.
        rated_power (float): The maximum rated power of the turbine in kW.
        yield_table (list): A list of dictionaries defining wind speed to yield percentage mapping.
        min_operational_wind_ms (int): Minimum wind speed for the turbine to operate.
        cutoff_wind_ms (int): Wind speed at which the turbine shuts down for safety.

    Returns:
        float: The calculated power output in kW. Returns 0 if wind speed is outside
               operational limits or causes damage.
    """
    # This function needs to be available to the agent.
    # It's duplicated here for simplicity, but in a real scenario, it would be in a shared library.
    if wind_speed < min_operational_wind_ms or wind_speed >= cutoff_wind_ms:
        return 0
    yield_str = get_power_yield_for_wind(wind_speed, yield_table)
    if yield_str == "damage":
        return 0
    yield_percent = parse_yield(yield_str)
    return rated_power * (yield_percent / 100.0)


def get_power_yield_for_wind(wind_speed, yield_table):
    """
    Retrieves the power yield percentage string for a given wind speed from the yield table.

    Args:
        wind_speed (int): Current wind speed in m/s.
        yield_table (list): A list of dictionaries defining wind speed to yield percentage mapping.

    Returns:
        str: The yield percentage as a string (e.g., "80", "70-90", "damage") or "0" if not found.
    """
    # Iterate through the yield table to find the matching wind speed or range.
    for item in yield_table:
        if "windMs" in item and item["windMs"] == wind_speed:
            return item["yieldPercent"]
        if "windMsRange" in item:
            range_str = item["windMsRange"]
            if "+" in range_str:
                if wind_speed >= int(range_str.replace("+", "")):
                    return item["yieldPercent"]
            elif "-" in range_str:
                low, high = map(int, range_str.split("-"))
                if low <= wind_speed <= high:
                    return item["yieldPercent"]
    return "0"


def parse_yield(yield_str):
    """
    Parses a yield percentage string into a float. Handles single values or ranges.

    Args:
        yield_str (str or int or float): The yield percentage as a string (e.g., "80", "70-90")
                                         or a direct numeric value.

    Returns:
        float: The parsed yield percentage. For ranges, it returns the average.
    """
    if isinstance(yield_str, (int, float)):
        return float(yield_str)
    if "-" in yield_str:
        low, high = map(int, yield_str.split("-"))
        return (low + high) / 2
    return float(yield_str)


class ConfigGeneratorAgent(BaseTask):
    """
    An agent responsible for generating wind turbine configurations based on weather forecasts,
    power plant deficit, and turbine documentation.

    It determines whether turbines should be in 'idle' (safety) or 'production' mode
    and calculates the pitch angle. It then requests unlock codes for the selected
    configurations.
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the ConfigGeneratorAgent.

        Args:
            agent_model: The underlying agent model.
            memory: The memory object for storing and retrieving data.
        """
        super().__init__(agent=agent_model, memory=memory, name="ConfigGeneratorAgent")

    def execute(self):
        """
        Executes the configuration generation logic.

        It retrieves necessary data from memory (forecast, powerplant status, documentation),
        calculates required power, and then iterates through the forecast to determine
        turbine modes and pitch angles. It prioritizes safety configurations and then
        selects production candidates. Finally, it requests unlock codes for the
        chosen configurations.
        """
        # Retrieve necessary data from memory.
        task_name = self.memory.get("task_name")
        forecast = self.memory.get("forecast")
        powerplant = self.memory.get("powerplant")
        rated_power = self.memory.get("rated_power")
        wind_yield_table = self.memory.get("wind_yield_table")
        max_wind_speed = self.memory.get("max_wind_speed")
        min_operational_wind_ms = self.memory.get("min_operational_wind_ms")

        # Extract the required power from the powerplant deficit string.
        # The deficit string is expected to be in a format like "X-Y kW", we need Y.
        deficit_str = powerplant["powerDeficitKw"]
        required_power = int(re.search(r"(\d+)-(\d+)", deficit_str).group(2))

        # Dictionaries to store configurations:
        # safety_configs for times when wind speed is too high.
        # production_candidates for times when turbines can generate power.
        safety_configs = {}
        production_candidates = []

        # Iterate through each forecast entry to determine potential configurations.
        for entry in forecast["forecast"]:
            date_str, wind = entry["timestamp"], entry["windMs"]
            # If wind speed exceeds the maximum safe operating speed, set to idle.
            if wind >= max_wind_speed:
                safety_configs[date_str] = {
                    "pitchAngle": 90,
                    "turbineMode": "idle",
                    "wind": wind,
                }
            # If wind speed is within operational limits, calculate potential power.
            elif min_operational_wind_ms <= wind < max_wind_speed:
                power = calculate_power(
                    wind,
                    rated_power,
                    wind_yield_table,
                    min_operational_wind_ms,
                    max_wind_speed,
                )
                production_candidates.append(
                    {"date": date_str, "power": power, "wind": wind}
                )

        # Sort production candidates by power output in descending order to prioritize higher generation.
        production_candidates.sort(key=lambda x: x["power"], reverse=True)

        # Initialize final configurations. The goal is to select up to 4 configurations.
        final_configs = {}

        # First, add all safety-related configurations.
        for date_str, data in safety_configs.items():
            # Ensure we don't exceed the maximum number of configurations (e.g., 4).
            if len(final_configs) < 4:
                final_configs[date_str] = {
                    "pitchAngle": data["pitchAngle"],
                    "turbineMode": data["turbineMode"],
                    "wind": data["wind"],
                }

        # Then, add production candidates until the limit is reached or all candidates are processed.
        for candidate in production_candidates:
            # Add if we haven't reached the limit and this date hasn't already been configured (e.g., for safety).
            if len(final_configs) < 4 and candidate["date"] not in final_configs:
                final_configs[candidate["date"]] = {
                    "pitchAngle": 0,
                    "turbineMode": "production",
                    "wind": candidate["wind"],
                }

        # If any configurations were selected, proceed to request unlock codes.
        if final_configs:
            # Update the expected results count in memory to include the unlock codes.
            expected_results = self.memory.get("expected_results_count")
            expected_results["unlockCodeGenerator"] = len(final_configs)
            self.memory.set("expected_results_count", expected_results)

            # Store configurations (without wind speed) for later matching with unlock codes.
            generated_configs_for_matching = {}
            for date_str, config in final_configs.items():
                # Prepare the payload for requesting an unlock code.
                payload = {
                    "action": "unlockCodeGenerator",
                    # Format date and hour as required by the API.
                    "startDate": datetime.fromisoformat(date_str).strftime("%Y-%m-%d"),
                    "startHour": datetime.fromisoformat(date_str).strftime("%H:%M:%S"),
                    "pitchAngle": config["pitchAngle"],
                    "windMs": float(config["wind"]),
                }
                # Send the request for an unlock code. The result will be polled by ResultsPollingAgent.
                verify_answer(task_name, payload)
                # Store the config (excluding wind speed, as it's not part of the final config)
                # keyed by date_str for later matching with the unlock code.
                generated_configs_for_matching[date_str] = {
                    k: v for k, v in config.items() if k != "wind"
                }

            # Save the generated configurations (without unlock codes yet) to memory.
            # This will be used by ConfigApplierAgent to combine with actual unlock codes.
            self.memory.set(
                "generated_configs_for_matching", generated_configs_for_matching
            )
