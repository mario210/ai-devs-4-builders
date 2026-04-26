from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class FieldCommanderAgent(BaseTask):
    """
    Manages the deployment and command of units on the field.

    This agent is responsible for executing a pre-defined plan from memory, which includes:
    - Creating units (transporters with scouts).
    - Moving them to designated deployment zones.
    - Dismounting scouts from transporters.
    - Commanding scouts to inspect specific tiles within their assigned zones.

    It interacts with the game's API via `verify_answer` to perform actions like
    creating, moving, dismounting, and inspecting units. It also maintains an internal
    state of the units it controls (transporters and scouts).
    """

    def __init__(self, agent_model, memory):
        """Initializes the FieldCommanderAgent."""
        super().__init__(agent=agent_model, memory=memory, name="FieldCommanderAgent")
        self.memory = memory
        self.task_name = self.memory.get("task_name")
        self.transporters = (
            []
        )  # List to store transporter objects {hash, position, passengers}
        self.scouts = []  # List to store scout objects {hash, position}
        self.road_coordinates = []  # To store road coordinates for transporter movement

    def _get_distant_road_coordinates(self):
        """
        Retrieves the specific truck deployment destinations from memory.
        Returns a list of tuples: (destination_coordinate, block_zone_name)
        """
        deployment_points = []
        # These zones are determined by the MapAnalysisAgent and are the target areas for deployment.
        zones = ["block3_north", "block3_south_east", "block3_south_west"]
        for zone in zones:
            dest = self.memory.get(f"{zone}_truck_deployment_destination")
            if dest:
                deployment_points.append((dest, zone))

        return deployment_points

    def _create_unit(self, initial_units_plan):
        """
        Creates a single unit based on the initial_units_plan and stores its details.
        Returns the created unit's hash and type.
        Raises an exception if creation fails or response is incomplete.
        """
        create_params = {"action": "create", "type": initial_units_plan["type"]}
        if "passengers" in initial_units_plan:
            create_params["passengers"] = initial_units_plan["passengers"]

        print(
            f"FieldCommanderAgent: Sending create action with params: {create_params}"
        )
        # Call the game API to create the unit.
        create_response = verify_answer(self.task_name, create_params)
        print(f"FieldCommanderAgent: Create action response: {create_response}")

        # Validate the response from the API.
        if (
            not create_response
            or "object" not in create_response
            or "spawn" not in create_response
        ):
            raise ValueError(
                f"Failed to create unit. Incomplete response: {create_response}"
            )

        unit_hash = create_response["object"]
        unit_position = create_response["spawn"]  # This is the initial spawn position
        unit_type = initial_units_plan["type"]

        # Store the created unit in the appropriate list for internal tracking.
        if unit_type == "transporter":
            self.transporters.append(
                {
                    "hash": unit_hash,
                    "position": unit_position,
                    "passengers": initial_units_plan.get("passengers", 0),
                }
            )
        elif unit_type == "scout":
            self.scouts.append({"hash": unit_hash, "position": unit_position})
        # No explicit storage for other types, if any.

        print(
            f"FieldCommanderAgent: Unit '{unit_hash}' ({unit_type}) created at {unit_position}."
        )
        return {"hash": unit_hash, "type": unit_type, "position": unit_position}

    def _move_unit_to_destination(self, unit_details, destination):
        """
        Queues movement for a unit to a specified destination.
        Raises an exception if movement queuing fails.
        """
        unit_hash = unit_details["hash"]
        unit_type = unit_details["type"]

        print(
            f"FieldCommanderAgent: Move unit '{unit_hash}' ({unit_type}) to {destination}..."
        )
        move_unit_params = {"action": "move", "object": unit_hash, "where": destination}
        # Call the game API to move the unit.
        move_unit_response = verify_answer(self.task_name, move_unit_params)
        print(
            f"FieldCommanderAgent: Move action response for unit '{unit_hash}' to {destination}: {move_unit_response}"
        )

        # The API documentation indicates 'code: 20' for a successful move queue.
        if not move_unit_response or move_unit_response.get("code") != 20:
            raise ValueError(
                f"Failed to queue movement for unit '{unit_hash}' to {destination}. Response: {move_unit_response}"
            )
        else:
            print(
                f"FieldCommanderAgent: Unit '{unit_hash}' successfully queued for movement to {destination}."
            )

        # Update the unit's stored position to its destination (assuming move is instantly queued).
        # This might need adjustment if movement is asynchronous and position updates later.
        if unit_type == "transporter":
            for t in self.transporters:
                if t["hash"] == unit_hash:
                    t["position"] = destination
                    break
        elif unit_type == "scout":
            for s in self.scouts:
                if s["hash"] == unit_hash:
                    s["position"] = destination
                    break

    def _dismount_scouts(self, transport_unit_hash, initial_units_plan):
        """
        Dismounts scouts from a transporter.
        Returns the response from the API.
        """
        print(f"FieldCommanderAgent: Dismount scout from unit '{transport_unit_hash}'")

        if "passengers" not in initial_units_plan:
            raise ValueError(
                f"Error: 'passengers' not found in initial_units_plan for dismount. Skipping dismount for {transport_unit_hash}."
            )

        dismount_scout_params = {
            "action": "dismount",
            "object": transport_unit_hash,
            "passengers": initial_units_plan["passengers"],
        }
        # Call the game API to dismount passengers.
        dismount_scout_response = verify_answer(self.task_name, dismount_scout_params)
        print(
            f"FieldCommanderAgent: Dismount action response for unit '{transport_unit_hash}' : {dismount_scout_response}"
        )
        return dismount_scout_response

    def _register_dismounted_scouts(self, dismount_scout_response):
        """
        Extracts dismounted scouts from the response and adds them to the agent's tracked list.
        Returns a list of scout unit hashes.
        """
        # The API response for a successful dismount includes a 'spawned' list.
        if not (
            dismount_scout_response
            and isinstance(dismount_scout_response.get("spawned"), list)
        ):
            print(
                f"FieldCommanderAgent: Dismount response did not contain expected 'spawned' list or was empty: {dismount_scout_response}"
            )
            return []

        newly_spawned_scouts = dismount_scout_response["spawned"]
        processed_scouts = []

        # Process each newly spawned scout from the API response.
        for scout_info in newly_spawned_scouts:
            scout_hash = scout_info.get("scout")
            scout_position = scout_info.get("where")

            if not scout_hash or not scout_position:
                print(
                    f"FieldCommanderAgent: Incomplete scout info from dismount: {scout_info}"
                )
                continue

            processed_scouts.append(scout_hash)
            # Add the newly spawned scout to our internal list for tracking.
            self.scouts.append({"hash": scout_hash, "position": scout_position})
            print(
                f"FieldCommanderAgent: Dismounted scout '{scout_hash}' spawned at {scout_position}."
            )

        return processed_scouts

    def _inspect_zone(self, target_zone_coords, scout_hashes):
        """
        Moves scouts to target tiles in a zone and inspects them.
        """
        # Loop through all tiles in the current zone, assign a scout, move it, and inspect.
        for idx, target_tile in enumerate(target_zone_coords):
            # Distribute the inspection tasks among the available scouts.
            # This cycles through the scouts for each tile.
            scout_unit_hash = scout_hashes[idx % len(scout_hashes)]

            # Move scout to the target tile.
            self._move_unit_to_destination(
                {"hash": scout_unit_hash, "type": "scout"}, target_tile
            )

            # After moving, command the scout to inspect the tile.
            inspect_scout_params = {"action": "inspect", "object": scout_unit_hash}
            inspect_scout_response = verify_answer(self.task_name, inspect_scout_params)
            print(
                f"FieldCommanderAgent: Inspect action response for scout '{scout_unit_hash}' at {target_tile}: {inspect_scout_response}"
            )

    def execute(self):
        """
        Executes the main logic of the agent.

        The process is as follows:
        1. Retrieve the initial unit creation plan and map analysis from memory.
        2. Identify the deployment points for transporters.
        3. For each deployment point:
            a. Create a transporter unit with scout passengers.
            b. Move the transporter to the deployment point.
            c. Dismount the scouts.
            d. Register the new scout units.
            e. Command the scouts to inspect all tiles in their assigned zone.
        """
        print("FieldCommanderAgent: Starting execution of the plan...")
        # Retrieve necessary data from shared memory.
        initial_units_plan = self.memory.get("initial_units_plan")
        map_analysis = self.memory.get("map_analysis")

        if not initial_units_plan:
            print(
                "FieldCommanderAgent: No initial unit creation plan found in memory. Exiting."
            )
            return

        if map_analysis:
            self.road_coordinates = map_analysis.get("road_coordinates", [])

        # Get the list of deployment points for the trucks from memory.
        deployment_points = self._get_distant_road_coordinates()

        if not deployment_points:
            print(
                "FieldCommanderAgent: No truck deployment destinations found in memory. Exiting."
            )
            return

        # Data from memory might be in a list wrapper. This handles that inconsistency.
        # The expected format for unit creation parameters is a dictionary.
        if (
            isinstance(initial_units_plan, list)
            and len(initial_units_plan) == 1
            and isinstance(initial_units_plan[0], dict)
        ):
            # Extract the actual unit plan dictionary from the list.
            initial_units_plan = initial_units_plan[0]
            # The 'action' key is part of the planner's output, not the 'create' API call.
            initial_units_plan.pop("action", None)

        # Final validation of the plan format before proceeding.
        if not isinstance(initial_units_plan, dict) or "type" not in initial_units_plan:
            print(
                f"FieldCommanderAgent: Invalid initial_units_plan format: {initial_units_plan}. Expected a dictionary with 'type' key. Exiting."
            )
            return

        # Iterate through each designated deployment zone and execute the deployment sequence.
        for i, (destination, current_zone) in enumerate(deployment_points):
            print(
                f"FieldCommanderAgent: Deploying unit {i + 1} to {destination} for {current_zone}..."
            )

            try:
                # Step 1: Create the unit (transporter with scouts).
                unit_details = self._create_unit(initial_units_plan)

                # Step 2: Move the newly created transport unit to its destination.
                self._move_unit_to_destination(unit_details, destination)

                # Step 3: Dismount scouts from the transporter.
                dismount_response = self._dismount_scouts(
                    unit_details["hash"], initial_units_plan
                )

                # Step 4: Register the newly dismounted scouts for tracking.
                scout_hashes = self._register_dismounted_scouts(dismount_response)
                if not scout_hashes:
                    print(
                        f"FieldCommanderAgent: No scouts available for {current_zone}."
                    )
                    continue

                # Retrieve the coordinates for the zone to be inspected.
                target_zone_coords = self.memory.get(current_zone)
                if not target_zone_coords and map_analysis:
                    target_zone_coords = map_analysis.get(current_zone, [])

                if not target_zone_coords:
                    print(
                        f"FieldCommanderAgent: No coordinates found for {current_zone}."
                    )
                    continue

                # Step 5: Command scouts to inspect the zone.
                self._inspect_zone(target_zone_coords, scout_hashes)

            except Exception as e:
                # Catch any errors during the process for a single unit to allow others to proceed.
                print(
                    f"FieldCommanderAgent: An unexpected error occurred during unit deployment for destination {destination}: {e}"
                )

        print("FieldCommanderAgent: Finished attempting to deploy initial units.")
