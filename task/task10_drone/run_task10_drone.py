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
from ai.orchestrator import AgentOrchestrator
from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


class MapAnalyzerTask(BaseTask):
    """Task responsible for analyzing the map and finding the dam's coordinates."""

    def execute(self) -> None:
        hub_data_url = os.environ.get("HUB_DATA_BASE_URL")
        image_url = f"{hub_data_url}/{AGENTS_API_KEY}/drone.png"
        self.memory.set("image_url", image_url)

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

        print(f"[{self.name}] Analyzing image from: {image_url}")
        response = self.agent.chat(messages=messages_map)

        print(f"\n--- [{self.name}] Response ---")
        print(response)
        print("-----------------------------------")

        # Safely parse and store data in shared memory
        try:
            dam_data = json.loads(response)
            parsed_location = (
                f"column {dam_data.get('column')}, row {dam_data.get('row')}"
            )
            self.memory.set("dam_location", parsed_location)
        except json.JSONDecodeError:
            print(
                f"[{self.name}] Warning: Map Analyzer output was not valid JSON. Using raw response."
            )
            self.memory.set("dam_location", response)


class FetchDocumentationTask(BaseTask):
    """Task responsible for retrieving API documentation."""

    def execute(self) -> None:
        hub_dane_url = os.environ.get("HUB_DANE_BASE_URL")
        doc_url = f"{hub_dane_url}/drone.html"
        print(f"[{self.name}] Fetching documentation from {doc_url}")
        try:
            doc_html = requests.get(doc_url, verify=False).text
            self.memory.set("api_docs", doc_html)
        except Exception as e:
            print(f"[{self.name}] Failed to fetch documentation: {e}")
            self.memory.set("api_docs", "")


class HackerTask(BaseTask):
    """Task responsible for programming the drone to reroute to the dam."""

    def __init__(self, name: str, agent, memory, max_retries: int = 20):
        super().__init__(name, agent, memory)
        self.max_retries = max_retries

    def execute(self) -> None:
        # Retrieve necessary context from shared memory
        doc_html = self.memory.get("api_docs")
        dam_location = self.memory.get("dam_location")

        hacker_prompt = f"""
Here is the Drone API Documentation:
{doc_html}

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
                "content": "You are a hacker agent programming a drone. Output only a JSON list of instructions.",
            },
            {"role": "user", "content": hacker_prompt},
        ]

        print(f"[{self.name}] Resetting drone before reconfiguration")
        hardReset = verify_answer("drone", {"instructions": ["hardReset"]})
        print(f"[{self.name}] HardReset Response: {hardReset}")

        for attempt in range(self.max_retries):
            print(f"\n--- [{self.name}] Attempt {attempt + 1}/{self.max_retries} ---")
            hacker_response = self.agent.chat(messages=messages_hacker)

            print(f"\n--- [{self.name}] Generated Instructions ---")
            print(hacker_response)

            try:
                instructions = json.loads(hacker_response)

                # Send verification request
                verification_response = verify_answer(
                    "drone", {"instructions": instructions}
                )
                print(f"[{self.name}] Verification Response: {verification_response}")

                # Check if the code is 0 (success)
                if verification_response.get("code") == 0:
                    print(f"\n--- [{self.name}] Task Completed Successfully! ---")
                    print(f"Flag/Message: {verification_response.get('message')}")
                    break
                else:
                    error_message = verification_response.get(
                        "message", "Unknown error"
                    )
                    print(
                        f"\n--- [{self.name}] Validation Failed. Asking Agent to fix... ---"
                    )

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
                    f"[{self.name}] Could not parse JSON instructions. Requesting a fix..."
                )
                messages_hacker.append(
                    {"role": "assistant", "content": hacker_response}
                )
                messages_hacker.append(
                    {
                        "role": "user",
                        "content": "The output was not valid JSON. Please provide ONLY a valid JSON list without any markdown wrappers. Do not include any explanations.",
                    }
                )


def run_task10_drone_orchestrator_way(agent_model):
    # Create a single shared agent to reduce instantiation overhead
    shared_agent = Agent(default_model=agent_model)

    orchestrator = AgentOrchestrator()
    orchestrator.add_task(
        MapAnalyzerTask(
            name="MapAnalyzer", agent=shared_agent, memory=orchestrator.memory
        )
    )
    orchestrator.add_task(
        FetchDocumentationTask(
            name="DocFetcher", agent=None, memory=orchestrator.memory
        )
    )
    orchestrator.add_task(
        HackerTask(name="DroneHacker", agent=shared_agent, memory=orchestrator.memory)
    )

    orchestrator.run()
    shared_agent.print_usage_statistics()


if __name__ == "__main__":
    run_task10_drone_orchestrator_way("openai/gpt-5.4")
