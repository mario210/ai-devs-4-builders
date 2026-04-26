from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer
import json
import os


class MapAnalystAgent(BaseTask):
    """
    The MapAnalystAgent is responsible for retrieving, analyzing, and storing geographical map data.
    It can either load pre-analyzed map data from a local file (`map_analysis.md`)
    or fetch it directly from the central hub API.

    Its primary goal is to extract key features like block coordinates, road coordinates,
    and specific clusters within 'block3' areas, making this information available
    to other agents via shared memory.
    """

    def __init__(self, agent_model, memory):
        """
        Initializes the MapAnalystAgent.

        Args:
            agent_model: The underlying AI model (though not directly used for map analysis here,
                         it's part of the BaseTask interface).
            memory: The shared memory object where agents store and retrieve information.
        """
        super().__init__(agent=agent_model, memory=memory, name="MapAnalystAgent")
        self.memory = memory
        self.task_name = self.memory.get("task_name")
        # Define the path to the map analysis file relative to this script
        # This file is used to cache map analysis results to avoid repeated API calls.
        self.map_file_path = os.path.join(
            os.path.dirname(__file__), "..", "map_analysis.md"
        )

    def execute(self):
        """
        Executes the map analysis process.
        """
        print("MapAnalystAgent: Starting map analysis...")

        # Check if the map analysis file already exists
        if os.path.exists(self.map_file_path):
            print(
                "MapAnalystAgent: map_analysis.md already exists. Reading from file instead of API..."
            )
            try:
                # Basic parsing of the existing markdown file to repopulate memory
                # This is a simplified approach, assuming the file structure hasn't been manually broken
                # The goal is to quickly load previously computed map features.
                with open(self.map_file_path, "r") as f:
                    content = f.read()

                # We need road_coordinates and block_coordinates for other agents.
                # Let's extract them using simple string searching/parsing since we control the format.

                def extract_section(content_str, start_str, end_str):
                    """
                    Helper function to extract a specific section (e.g., JSON block)
                    from the markdown analysis file based on start and end markers.

                    Args:
                        content_str (str): The full content of the markdown file.
                        start_str (str): The marker indicating the beginning of the desired section.
                        end_str (str): The marker indicating the end of the desired section.

                    Returns:
                        list or dict or str or None: The parsed content (JSON or raw text)
                                                     or None if the section is not found/parsed.
                    """
                    start_marker = start_str
                    end_marker = end_str

                    start_idx = content_str.find(start_marker)
                    if start_idx == -1:
                        return None  # Or [] depending on expected type

                    # Adjust start_idx to point to the beginning of the JSON content
                    json_start_idx = content_str.find("\n", start_idx) + 1

                    end_idx = content_str.find(end_marker, json_start_idx)
                    if end_idx == -1:
                        # If end marker not found, assume it's the end of the file
                        json_str = content_str[json_start_idx:].strip()
                    else:
                        json_str = content_str[json_start_idx:end_idx].strip()

                    # Remove markdown code block fences if present
                    if json_str.startswith("```json"):
                        json_str = json_str[len("```json") :].strip()
                    if json_str.startswith("```text"):  # For formatted_map_str
                        json_str = json_str[len("```text") :].strip()
                    if json_str.endswith("```"):
                        json_str = json_str[: -len("```")].strip()

                    try:
                        if (
                            start_str == "### Full Map Grid:"
                        ):  # Special handling for text grid
                            return json_str
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        print(
                            f"MapAnalystAgent: Warning - Could not parse section {start_str}. Error: {e}"
                        )
                        return None  # Or []

                # Extract various map features from the loaded file content.
                block_coords = extract_section(
                    content,
                    "### Identified Blocks (block1, block2, block3):",
                    "\n\n### Identified Roads",
                )

                # Try new format for road coordinates first, then fallback to older format if needed.
                road_coords = extract_section(
                    content, "### Identified Roads (road):", "\n\n### Block3 North:"
                )
                if road_coords is None:  # Fallback to old marker
                    road_coords = extract_section(
                        content,
                        "### Identified Roads (road):",
                        "\n\n### Tile Information:",
                    )

                block3_north = extract_section(
                    content, "### Block3 North:", "\n\n### Block3 South-East:"
                )
                block3_south_east = extract_section(
                    content, "### Block3 South-East:", "\n\n### Block3 South-West:"
                )
                block3_south_west = extract_section(
                    content, "### Block3 South-West:", "\n\n### Tile Information:"
                )
                tiles_info = extract_section(
                    content, "### Tile Information:", "END_OF_FILE_MARKER"
                )  # Use a marker that won't be found to read till end
                formatted_map_str = extract_section(
                    content,
                    "### Full Map Grid:",
                    "\n\n### Identified Blocks (block1, block2, block3):",
                )

                analysis_report = {
                    "block_coordinates": (
                        block_coords if block_coords is not None else []
                    ),
                    "road_coordinates": road_coords if road_coords is not None else [],
                    "full_map_grid": [],  # We don't store the parsed grid directly from file for now
                    "formatted_map_str": (
                        formatted_map_str if formatted_map_str is not None else ""
                    ),
                    "tiles_info": tiles_info if tiles_info is not None else {},
                }

                self.memory.set("map_analysis", analysis_report)
                self.memory.set(
                    "block3_north", block3_north if block3_north is not None else []
                )
                self.memory.set(
                    "block3_south_east",
                    block3_south_east if block3_south_east is not None else [],
                )
                self.memory.set(
                    "block3_south_west",
                    block3_south_west if block3_south_west is not None else [],
                )
                print("MapAnalystAgent: Map analysis loaded from file.")

                # Verify if the loaded data is complete enough; if so, skip API call.
                # Verify we actually got the data, if not fallback to API
                is_new_format = "### Block3 North:" in content
                if (
                    block_coords
                    and road_coords
                    and is_new_format
                    and tiles_info
                    and formatted_map_str
                ):
                    return  # Exit early, skip API call
                else:
                    print(
                        "MapAnalystAgent: Parsed data is incomplete or empty. Falling back to API."
                    )

            except Exception as e:
                print(
                    f"MapAnalystAgent: Error reading existing map file: {e}. Will fallback to API."
                )

        # If file doesn't exist or reading fails, proceed with API call
        print("MapAnalystAgent: Fetching map from API...")
        response = verify_answer(self.task_name, {"action": "getMap"})

        # Validate the API response structure.

        if not response or "map" not in response:
            print("MapAnalystAgent: Failed to retrieve map data or 'map' key missing.")
            return

        map_details = response["map"]
        grid = map_details["grid"]
        tiles_info = map_details["tiles"]

        # Initialize lists to store extracted coordinates.
        block_coordinates = []
        road_coordinates = []
        num_rows = len(grid)
        num_cols = len(grid[0]) if num_rows > 0 else 0

        # Create a formatted grid for logging with A-K (columns) and 1-11 (rows) headers.
        # The top-left corner (0,0) is left empty for alignment.
        formatted_grid = [[""] + [chr(65 + c) for c in range(num_cols)]]

        for r_idx, row in enumerate(grid):
            formatted_row = [str(r_idx + 1)]
            for c_idx, cell_label in enumerate(
                row
            ):  # cell_label will be 'road', 'block1', 'tree', etc.
                formatted_row.append(cell_label)
                # Convert 0-indexed coordinates to A1-style coordinates
                coord = f"{chr(65 + c_idx)}{r_idx + 1}"

                if cell_label.startswith("block"):  # 'block1', 'block2', 'block3'
                    block_coordinates.append(coord)
                elif cell_label == "road":  # 'road'
                    road_coordinates.append(coord)
            formatted_grid.append(formatted_row)

        # Create a visually aligned string representation of the map
        # This helps in debugging and understanding the map layout.
        col_widths = [
            max(len(str(item)) for item in col) for col in zip(*formatted_grid)
        ]
        log_lines = []
        for row in formatted_grid:
            log_lines.append(
                " | ".join(
                    str(item).ljust(width) for item, width in zip(row, col_widths)
                )
            )

        formatted_map_str = "\n".join(log_lines)
        # Identify specific clusters of 'block3' cells, which might represent distinct buildings or areas.
        # Analyze grid for specific block3 buildings
        block3_north, block3_south_east, block3_south_west = self._find_block3_clusters(
            grid
        )

        analysis_report = {
            "block_coordinates": block_coordinates,
            "road_coordinates": road_coordinates,
            "full_map_grid": grid,
            "formatted_map_str": formatted_map_str,
            "tiles_info": tiles_info,
        }  # Store the comprehensive analysis report.

        # Save the analysis to a markdown file for caching and human readability.
        # Save the analysis to a file
        with open(self.map_file_path, "w") as f:
            f.write("## Map Analysis Report\n\n")
            f.write("### Full Map Grid:\n")
            f.write("```text\n")
            f.write(formatted_map_str)
            f.write("\n```\n")
            f.write("\n\n### Identified Blocks (block1, block2, block3):\n")
            f.write("```json\n")
            f.write(json.dumps(block_coordinates, indent=2))
            f.write("\n```\n")
            f.write("\n\n### Identified Roads (road):\n")
            f.write("```json\n")
            f.write(json.dumps(road_coordinates, indent=2))
            f.write("\n```\n")
            f.write("\n\n### Block3 North:\n")
            f.write("```json\n")
            f.write(json.dumps(block3_north, indent=2))
            f.write("\n```\n")
            f.write("\n\n### Block3 South-East:\n")
            f.write("```json\n")
            f.write(json.dumps(block3_south_east, indent=2))
            f.write("\n```\n")
            f.write("\n\n### Block3 South-West:\n")
            f.write("```json\n")
            f.write(json.dumps(block3_south_west, indent=2))
            f.write("\n```\n")
            f.write("\n\n### Tile Information:\n")
            f.write("```json\n")
            f.write(json.dumps(tiles_info, indent=2))
            f.write("\n```")

        print(
            f"MapAnalystAgent: Map analysis complete. Report saved to {self.map_file_path}"
        )
        # Update shared memory with the analysis results for other agents to use.
        self.memory.set("map_analysis", analysis_report)
        self.memory.set("block3_north", block3_north)
        self.memory.set("block3_south_east", block3_south_east)
        self.memory.set("block3_south_west", block3_south_west)

    def _find_block3_clusters(self, grid):
        """
        Identifies and categorizes clusters of 'block3' cells within the grid.
        It uses a simple connected components algorithm (BFS-like) to find clusters
        and then categorizes them into 'north', 'south-east', and 'south-west'
        based on their average coordinates.

        Args:
            grid (list of list of str): The 2D grid representing the map.

        Returns:
            tuple: A tuple containing three lists of coordinates (north, south-east, south-west clusters).
                   Each list contains A1-style coordinates of the cells in that cluster.
        """
        block3_cells = []
        for r in range(len(grid)):
            for c in range(len(grid[r])):
                if grid[r][c] == "block3":
                    block3_cells.append((r, c))

        clusters = []
        visited = set()  # Keep track of visited cells to avoid reprocessing.
        # Define all 8 possible directions for checking neighbors (including diagonals).
        directions = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        for r, c in block3_cells:
            if (r, c) not in visited:
                cluster = []
                queue = [(r, c)]
                visited.add((r, c))
                # Perform a BFS-like traversal to find all connected 'block3' cells.
                while queue:
                    curr_r, curr_c = queue.pop(0)
                    # Convert 0-indexed grid coordinates to A1-style coordinates.
                    coord = f"{chr(65 + curr_c)}{curr_r + 1}"
                    cluster.append({"coord": coord, "r": curr_r, "c": curr_c})

                    # Check all neighbors.
                    for dr, dc in directions:
                        nr, nc = curr_r + dr, curr_c + dc
                        if (nr, nc) in block3_cells and (nr, nc) not in visited:
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                clusters.append(cluster)

        if not clusters:
            return [], [], []  # Return empty lists if no block3 clusters are found.

        # Calculate the average row and column for each cluster to determine its general position.
        cluster_info = []
        for c in clusters:
            avg_r = sum(cell["r"] for cell in c) / len(c)
            avg_c = sum(cell["c"] for cell in c) / len(c)
            # Sort coordinates for consistent output.
            coords_only = sorted([cell["coord"] for cell in c])
            cluster_info.append({"avg_r": avg_r, "avg_c": avg_c, "coords": coords_only})

        # Sort clusters primarily by average row (north to south) to identify the northernmost one.
        cluster_info.sort(key=lambda x: x["avg_r"])
        north_cluster = cluster_info[0]["coords"] if len(cluster_info) > 0 else []

        south_east_cluster = []
        south_west_cluster = []

        if len(cluster_info) >= 3:
            # If there are at least 3 clusters, the remaining ones are south.
            # Sort these southern clusters by average column to distinguish east from west.
            south_clusters = cluster_info[1:]
            south_clusters.sort(key=lambda x: x["avg_c"])
            south_west_cluster = south_clusters[0]["coords"]
            south_east_cluster = south_clusters[1]["coords"]
        elif len(cluster_info) == 2:
            # If only two clusters, the second one is considered south-west by this logic.
            # This might need refinement based on actual map layouts if there are only two block3 clusters
            # and their relative positions are not strictly north/south-east/south-west.
            # For now, assuming the problem implies 3 distinct clusters for block3.
            south_clusters = cluster_info[1:]
            south_clusters.sort(key=lambda x: x["avg_c"])
            south_west_cluster = south_clusters[0]["coords"]

        return north_cluster, south_east_cluster, south_west_cluster
