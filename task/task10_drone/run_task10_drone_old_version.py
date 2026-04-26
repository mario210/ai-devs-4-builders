import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sys
import os
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

# Ensure the AI_Devs4 root directory is in the path to import custom modules
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from ai.agent import Agent, AGENTS_API_KEY
from ai.tools.hub_requests import verify_answer


def analyze_map_subagent() -> str:
    """Sub-Agent responsible for analyzing the map and finding the dam's coordinates."""
    print("\n[Sub-Agent: MapAnalyzer] Initiating map analysis...")
    agent = Agent(default_model="openai/gpt-5.4")
    hub_data_url = os.environ.get("HUB_DATA_BASE_URL")
    image_url = f"{hub_data_url}/{AGENTS_API_KEY}/drone.png"

    prompt_text = (
        "Analyze the picture. The map is divided by a grid into sectors. "
        "Near the dam, the intensity of the water color was deliberately strengthened "
        "to make it easier to locate. "
        "Your goal: count the grid columns and rows, and locate the sector with the dam. "
        "Note the column and row number of the dam sector in the grid (indexing from 1). "
        "Return ONLY a valid JSON object containing exactly two keys: 'column' and 'row' with integer values. No markdown blocks."
    )

    messages_map = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    response = agent.chat(messages=messages_map)
    print(f"[Sub-Agent: MapAnalyzer] Analysis Complete. Response: {response}")

    try:
        dam_data = json.loads(response)
        return f"column {dam_data.get('column')}, row {dam_data.get('row')}"
    except json.JSONDecodeError:
        print(
            "[Sub-Agent: MapAnalyzer] Warning: Output was not valid JSON. Returning raw response."
        )
        return response


def fetch_docs_subagent() -> str:
    """Sub-Agent (Worker) responsible for retrieving API documentation."""
    print("\n[Sub-Agent: DocFetcher] Fetching API documentation...")
    hub_dane_url = os.environ.get("HUB_DANE_BASE_URL")
    doc_url = f"{hub_dane_url}/drone.html"
    try:
        doc_html = requests.get(doc_url, verify=False).text
        print("[Sub-Agent: DocFetcher] Successfully retrieved documentation.")
        return doc_html
    except Exception as e:
        print(f"[Sub-Agent: DocFetcher] Failed to fetch documentation: {e}")
        return f"Error fetching documentation: {e}"


def hack_drone_subagent(dam_location: str, api_docs: str) -> str:
    """Sub-Agent responsible for iterativley programming the drone using LLM and API."""
    print(
        f"\n[Sub-Agent: DroneHacker] Initiating drone hack targeting location: {dam_location}"
    )
    agent = Agent(default_model="openai/gpt-5.4")
    max_retries = 20

    hacker_prompt = f"""
Here is the Drone API Documentation:
{api_docs}

Twoim zadaniem jest zaprogramować drona tak, aby wyruszył z misją zrzucenia paczki do wymaganego obiektu, ale faktycznie paczka ma spaść nie na elektrownię, a na pobliską tamę.
Kod identyfikacyjny elektrowni w Żarnowcu: PWR6132PL.
The dam is located at this grid position: {dam_location}

Analyze the API documentation carefully. 
Use the described API methods to change the coordinates to the dam's location instead of the power plant.
The final result must be a list of instructions in JSON format as required by the documentation. 
Output ONLY the valid JSON list, without any markdown formatting (no ```json).
"""

    messages_hacker = [
        {
            "role": "system",
            "content": "You are a hacker ai programming a drone. Output only a JSON list of instructions.",
        },
        {"role": "user", "content": hacker_prompt},
    ]

    print("[Sub-Agent: DroneHacker] Resetting drone before reconfiguration")
    hardReset = verify_answer("drone", {"instructions": ["hardReset"]})
    print(f"[Sub-Agent: DroneHacker] HardReset Response: {hardReset}")

    for attempt in range(max_retries):
        print(f"\n--- [Sub-Agent: DroneHacker] Attempt {attempt + 1}/{max_retries} ---")
        hacker_response = agent.chat(messages=messages_hacker)

        try:
            instructions = json.loads(hacker_response)

            verification_response = verify_answer(
                "drone", {"instructions": instructions}
            )
            print(
                f"[Sub-Agent: DroneHacker] Verification Response: {verification_response}"
            )

            if verification_response.get("code") == 0:
                success_msg = f"Task Completed Successfully! Message/Flag: {verification_response.get('message')}"
                print(f"\n--- [Sub-Agent: DroneHacker] {success_msg} ---")
                return success_msg
            else:
                error_message = verification_response.get("message", "Unknown error")
                print("\n--- [Sub-Agent: DroneHacker] Validation Failed. Fixing... ---")

                messages_hacker.append(
                    {"role": "assistant", "content": hacker_response}
                )

                feedback_prompt = f"""
The instructions you provided resulted in an error:
"{error_message}"

This message is just a hint of what went wrong. Do NOT include this error message sentence in your output.
You must return only the JSON list containing the method names and their parameters as described in the documentation.
Please review the documentation again, fix the instructions based on the hint, and return the updated valid JSON list. Output ONLY the JSON list.
"""
                messages_hacker.append({"role": "user", "content": feedback_prompt})

        except json.JSONDecodeError:
            print(
                "[Sub-Agent: DroneHacker] Could not parse JSON instructions. Requesting a fix..."
            )
            messages_hacker.append({"role": "assistant", "content": hacker_response})
            messages_hacker.append(
                {
                    "role": "user",
                    "content": "The output was not valid JSON. Please provide ONLY a valid JSON list without any markdown wrappers.",
                }
            )

    return "Failed to hack the drone after maximum retries."


def run_task10_drone(agent_model):
    # Create the Main Supervisor Agent
    supervisor_agent = Agent(default_model=agent_model)

    # 1. Map the Tools to the Sub-Agent Functions
    tool_map = {
        "analyze_map": analyze_map_subagent,
        "fetch_api_docs": fetch_docs_subagent,
        "hack_drone": hack_drone_subagent,
    }

    # 2. Define the JSON Schemas for the Tools so the Supervisor understands how to use them
    tools = [
        {
            "type": "function",
            "function": {
                "name": "analyze_map",
                "description": "Analyzes the visual map to find the dam's grid coordinates (column and row). Call this first.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_api_docs",
                "description": "Fetches the API documentation required to program the drone. Call this second.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "hack_drone",
                "description": "Programs the drone to reroute to the dam. Requires the dam location and the API documentation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dam_location": {
                            "type": "string",
                            "description": "Coordinates of the dam (e.g., 'column X, row Y')",
                        },
                        "api_docs": {
                            "type": "string",
                            "description": "The raw text of the API documentation",
                        },
                    },
                    "required": ["dam_location", "api_docs"],
                },
            },
        },
    ]

    supervisor_prompt = """
    You are the Lead Drone Mission Supervisor.
    Your objective is to coordinate sub-agents to reroute a drone to drop its package on the nearby dam instead of the power plant.
    
    Delegation Instructions:
    1. Call 'analyze_map' to find the dam's coordinates.
    2. Call 'fetch_api_docs' to understand how to program the drone.
    3. Call 'hack_drone' passing the dam's location and the API docs to execute the reroute.
    
    After the drone is successfully hacked, provide a final concise summary of the operation and present the final flag to the user.
    """

    messages = [
        {"role": "system", "content": supervisor_prompt},
        {
            "role": "user",
            "content": "Execute the mission: reroute the drone to the dam.",
        },
    ]

    print("\n=========================================")
    print("=== SUPERVISOR AGENT: STARTING MISSION ===")
    print("=========================================")

    # 3. Give the Supervisor the reins. It will autonomously call the tools in sequence.
    # We set max_iterations=10 to ensure it has enough steps to call all 3 tools and respond.
    final_response = supervisor_agent.chat(
        messages=messages, tools=tools, tool_map=tool_map, max_iterations=10
    )

    print("\n=========================================")
    print("=== SUPERVISOR AGENT: FINAL REPORT ======")
    print("=========================================")
    print(final_response)
    supervisor_agent.print_usage_statistics()


if __name__ == "__main__":
    run_task10_drone("openai/gpt-5.4")
