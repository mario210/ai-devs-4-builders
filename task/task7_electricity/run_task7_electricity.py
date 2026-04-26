import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import requests
import base64
import re
import os
from dotenv import load_dotenv

from ai.tools.files import download_file
from ai.agent import Agent, AGENTS_API_KEY
from task.task7_electricity.task7_tools import submit_electricity_answer

# Load environment variables
load_dotenv()


# --- Task 7: Electricity ---
def run_task7_electricity(agent_model):
    print("\n--- Running Task 7: Electricity ---")
    agent = Agent(default_model=agent_model)

    # URLs and local filenames
    hub_data_url = os.environ.get("HUB_DATA_BASE_URL")
    hub_i_url = os.environ.get("HUB_I_BASE_URL")

    puzzle_url = f"{hub_data_url}/{AGENTS_API_KEY}/electricity.png"
    solved_url = f"{hub_i_url}/solved_electricity.png"
    solved_filename = (
        "data/solved_electricity.png"  # Changed to save in data/ directory
    )

    # --- Step 1: Prepare the solution image ---
    # Download the solution image if it doesn't exist locally.
    print(f"Preparing solution image: {solved_filename}...")
    download_result = download_file(solved_url, save_path=solved_filename)
    print(download_result)  # Print the result message from the tool

    if "Error downloading file" in download_result:
        print(f"Fatal: Could not download solution image. Details: {download_result}")
        return

    # Encode the static solution image once before the loop.
    try:
        with open(solved_filename, "rb") as image_file:
            solved_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    except IOError as e:
        print(f"Fatal: Could not read solution image '{solved_filename}': {e}")
        return

    # --- Step 2: Iteratively find differences and submit rotations ---
    max_rotations = 20  # Safety break to prevent infinite loops
    for i in range(max_rotations):
        print(f"\n--- Solving Iteration {i + 1}/{max_rotations} ---")

        # Fetch the latest puzzle image directly into memory.
        try:
            print(f"Fetching latest puzzle state from {puzzle_url}...")
            response = requests.get(puzzle_url)
            response.raise_for_status()
            puzzle_base64 = base64.b64encode(response.content).decode("utf-8")
        except requests.RequestException as e:
            print(f"Failed to fetch puzzle image on iteration {i + 1}: {e}. Aborting.")
            break

        find_diff_prompt_text = (
            "Analyze the two images provided. The first is the current puzzle, the second is the final solution. "
            "They are 3x3 grids of components. Find the coordinates of a single component in the puzzle image that is "
            "rotated differently than the corresponding component in the solution image. "
            "Return ONLY the coordinates as a string in 'RxC' format (e.g., '2x3' for row 2, column 3). "
            "If the images are identical and the puzzle is solved, return the exact string 'ALL_CORRECT'."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": find_diff_prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{puzzle_base64}"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{solved_base64}"},
                    },
                ],
            }
        ]

        coordinate_to_rotate = agent.chat(
            messages=messages,
            # No tools are needed for this specific call, as the ai can 'see' the images directly.
            max_iterations=1,
        )

        print(f"Agent analysis result: '{coordinate_to_rotate}'")

        if not coordinate_to_rotate or "ALL_CORRECT" in coordinate_to_rotate:
            print(
                "Agent analysis indicates the puzzle is solved (images match). Task complete."
            )
            break

        match = re.search(r"\d+x\d+", coordinate_to_rotate)
        if not match:
            print(
                f"Could not parse coordinates from ai response: '{coordinate_to_rotate}'. Aborting."
            )
            break

        coords = match.group(0)
        submission_response = submit_electricity_answer(coords)

        if submission_response:
            message = submission_response.get("message")
            if isinstance(message, str) and ("FLG" in message):
                print("Server confirms: PUZZLE SOLVED! Task complete.")
                break
    else:
        print(f"Reached max rotations ({max_rotations}) without solving the puzzle.")


if __name__ == "__main__":
    run_task7_electricity("google/gemini-3-flash-preview")
