from ai.task import BaseTask
import json

# --- Switch flag for LLM usage ---
USE_LLM_FOR_TRUCK_DEPLOYMENT = False


class LogisticianAgent(BaseTask):
    """
    The LogisticianAgent is responsible for high-level logistical planning at the
    start of a mission. Its primary tasks are:

    1.  **Initial Unit Creation:** Defines a plan to create essential starting units,
        such as a transporter for carrying other units.

    2.  **Truck Deployment Point Calculation:** Determines the optimal drop-off
        points on the road network for trucks to deliver resources or personnel to
        specific building clusters (in this case, 'block3' clusters).

    It operates in one of two modes, controlled by the `USE_LLM_FOR_TRUCK_DEPLOYMENT` flag:
    - **LLM Mode (True):** It dynamically analyzes the map by constructing a detailed
      prompt for a Large Language Model (LLM). The LLM is asked to identify the
      closest road tile to each building cluster. This allows for flexible and
      optimal routing based on the current map layout.
    - **Fallback Mode (False):** It uses a set of predefined, hardcoded coordinates
      as the deployment points. This ensures reliability if the LLM is disabled,
      unavailable, or fails to provide a valid response.

    The agent concludes by saving its plans (`initial_units_plan` and `truck_targets`)
    into shared memory for other agents (like a Commander or Executor) to act upon.
    """

    def __init__(self, agent_model, memory):
        super().__init__(agent=agent_model, memory=memory, name="LogisticianAgent")
        self.memory = memory

    def execute(self):
        print(
            "LogisticianAgent: Deciding on unit creation for the specific scout journey..."
        )

        initial_units_plan = [
            {"action": "create", "type": "transporter", "passengers": 1}
        ]

        # Get block3 building positions
        block3_north = self.memory.get("block3_north")
        block3_south_east = self.memory.get("block3_south_east")
        block3_south_west = self.memory.get("block3_south_west")

        block3_north_truck_deployment_destination = None
        block3_south_east_truck_deployment_destination = None
        block3_south_west_truck_deployment_destination = None

        if USE_LLM_FOR_TRUCK_DEPLOYMENT:
            # Get map analysis data for the LLM
            map_analysis = self.memory.get("map_analysis", {})
            formatted_map_str = map_analysis.get(
                "formatted_map_str", "Map not available."
            )
            tiles_info = map_analysis.get("tiles_info", {})
            road_coordinates = map_analysis.get("road_coordinates", [])

            # Construct the prompt for the LLM
            llm_prompt = f"""
You are an expert logistician agent. Your task is to analyze a map and identify the closest road tiles for specific building clusters.

Here is the map grid:
```text
{formatted_map_str}
```

Here is detailed information about all tiles, including their types and coordinates:
```json
{json.dumps(tiles_info, indent=2)}
```

Here are the coordinates of all identified road tiles:
```json
{json.dumps(road_coordinates, indent=2)}
```

Here are the coordinates for three specific block3 building clusters:
- Block3 North: {json.dumps(block3_north)}
- Block3 South-East: {json.dumps(block3_south_east)}
- Block3 South-West: {json.dumps(block3_south_west)}

For each of these three block3 clusters, find the single road tile that is closest to any of the tiles within that cluster.
The distance should be calculated using Manhattan distance (abs(x1-x2) + abs(y1-y2)) for simplicity, or Euclidean distance if you can infer precise coordinates from the A1-style coordinates.
Prioritize 'UL' roads if available and clearly distinguishable, otherwise use any 'road' tile.

Your output MUST be a JSON object with the following structure:
{{
    "block3_north_truck_deployment_destination": "A1-style coordinate of the nearest road tile",
    "block3_south_east_truck_deployment_destination": "A1-style coordinate of the nearest road tile",
    "block3_south_west_truck_deployment_destination": "A1-style coordinate of the nearest road tile"
}}
Ensure the output is valid JSON and contains only the JSON object.
"""
            print("LogisticianAgent: Calling LLM to find nearest road tiles...")
            llm_response = self.agent.chat(
                messages=[{"role": "user", "content": llm_prompt}]
            )
            print(f"LogisticianAgent: LLM raw response: {llm_response}")

            try:
                llm_output = json.loads(llm_response)
                block3_north_truck_deployment_destination = llm_output.get(
                    "block3_north_truck_deployment_destination"
                )
                block3_south_east_truck_deployment_destination = llm_output.get(
                    "block3_south_east_truck_deployment_destination"
                )
                block3_south_west_truck_deployment_destination = llm_output.get(
                    "block3_south_west_truck_deployment_destination"
                )

                # Check if all expected deployment points are present
                if not (
                    block3_north_truck_deployment_destination
                    and block3_south_east_truck_deployment_destination
                    and block3_south_west_truck_deployment_destination
                ):
                    print(
                        "LogisticianAgent: LLM response was incomplete. Falling back to default deployments."
                    )
                    use_llm_for_truck_deployment = False  # Force fallback if incomplete
                else:
                    self.memory.set(
                        "block3_north_truck_deployment_destination",
                        block3_north_truck_deployment_destination,
                    )
                    self.memory.set(
                        "block3_south_east_truck_deployment_destination",
                        block3_south_east_truck_deployment_destination,
                    )
                    self.memory.set(
                        "block3_south_west_truck_deployment_destination",
                        block3_south_west_truck_deployment_destination,
                    )
                    print(
                        "LogisticianAgent: LLM successfully identified truck deployment points."
                    )

            except json.JSONDecodeError as e:
                print(
                    f"LogisticianAgent: Error parsing LLM response: {e}. Raw response: {llm_response}. Falling back to default deployments."
                )
                use_llm_for_truck_deployment = False  # Force fallback if parsing fails
            except Exception as e:
                print(
                    f"LogisticianAgent: An unexpected error occurred with LLM response: {e}. Falling back to default deployments."
                )
                use_llm_for_truck_deployment = (
                    False  # Force fallback if any other error occurs
                )

        if not USE_LLM_FOR_TRUCK_DEPLOYMENT:
            print("LogisticianAgent: Using fallback truck deployment points.")
            block3_north_truck_deployment_destination = "E2"
            block3_south_east_truck_deployment_destination = "H9"
            block3_south_west_truck_deployment_destination = "B9"

            self.memory.set(
                "block3_north_truck_deployment_destination",
                block3_north_truck_deployment_destination,
            )
            self.memory.set(
                "block3_south_east_truck_deployment_destination",
                block3_south_east_truck_deployment_destination,
            )
            self.memory.set(
                "block3_south_west_truck_deployment_destination",
                block3_south_west_truck_deployment_destination,
            )

        truck_targets = []

        # Use the LLM-determined or fallback deployment points
        if block3_north and block3_north_truck_deployment_destination:
            # Assuming 'from' should be the first coordinate of each block3 cluster.
            # If a more specific 'from' point is needed, this logic should be adjusted.
            truck_targets.append(
                {
                    "from": block3_north[0],
                    "to": block3_north_truck_deployment_destination,
                }
            )
        if block3_south_east and block3_south_east_truck_deployment_destination:
            truck_targets.append(
                {
                    "from": block3_south_east[0],
                    "to": block3_south_east_truck_deployment_destination,
                }
            )
        if block3_south_west and block3_south_west_truck_deployment_destination:
            truck_targets.append(
                {
                    "from": block3_south_west[0],
                    "to": block3_south_west_truck_deployment_destination,
                }
            )

        print(
            f"LogisticianAgent: Truck routing plan: {json.dumps(truck_targets, indent=2)}"
        )

        self.memory.set("initial_units_plan", initial_units_plan)
        self.memory.set(
            "scout_deployment_points", []
        )  # Assuming this is for scouts, not trucks

        # NEW: truck movement plan
        self.memory.set("truck_targets", truck_targets)

        print("LogisticianAgent: Plans saved to memory (including truck routing).")
