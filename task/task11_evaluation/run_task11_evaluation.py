import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import json
from typing import Optional
import zipfile

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from ai.agent import Agent
from ai.orchestrator import AgentOrchestrator
from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer

# Load environment variables if they haven't been loaded already
from dotenv import load_dotenv

load_dotenv()

from langfuse import get_client

langfuse = get_client()


class SensorEvaluationTask(BaseTask):
    """Task responsible for evaluating sensor data and finding anomalies."""

    def _evaluate_batch_with_llm(self, prompt: str) -> list:
        """Helper method using explicit Langfuse SDK to trace the LLM call."""

        with langfuse.start_as_current_observation(
            as_type="span", name="evaluate_batch"
        ) as span:
            with langfuse.start_as_current_observation(
                as_type="generation", name="llm_evaluation", input=prompt
            ) as generation:
                try:
                    messages = [{"role": "user", "content": prompt}]
                    response = self.agent.chat(messages=messages)

                    cleaned_response = response.strip()
                    if cleaned_response.startswith("```json"):
                        cleaned_response = cleaned_response[7:-3].strip()
                    elif cleaned_response.startswith("```"):
                        cleaned_response = cleaned_response[3:-3].strip()

                    batch_anomalies = json.loads(cleaned_response)

                    generation.update(
                        output=batch_anomalies,
                        metadata={"found_anomalies": len(batch_anomalies)},
                    )
                    span.update(
                        output=f"Processed batch, found {len(batch_anomalies)} anomalies"
                    )
                    return batch_anomalies

                except Exception as e:
                    generation.update(level="ERROR", status_message=str(e))
                    span.update(level="ERROR", status_message=str(e))
                    raise e

    def _ensure_data_ready(self) -> Optional[str]:
        """
        Ensures the sensor data directory exists. If not, it checks for a sensors.zip file
        and extracts it. Returns the path to the data directory if successful, else None.
        """
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        data_dir = os.path.join(base_dir, "data", "sensors")

        if not os.path.exists(data_dir):
            print(f"[{self.name}] Directory {data_dir} not found.")
            zip_file_path = os.path.join(base_dir, "data", "sensors.zip")
            if os.path.exists(zip_file_path):
                print(f"[{self.name}] Found {zip_file_path}. Attempting to extract...")
                try:
                    os.makedirs(
                        data_dir, exist_ok=True
                    )  # Ensure target directory exists
                    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                        zip_ref.extractall(data_dir)
                    print(
                        f"[{self.name}] Successfully extracted {zip_file_path} to {data_dir}."
                    )
                    return data_dir
                except Exception as e:
                    print(f"[{self.name}] Error extracting {zip_file_path}: {e}")
                    print(
                        f"[{self.name}] Task aborted. Please ensure data is present in {data_dir} or {zip_file_path} is valid."
                    )
                    return None  # Exit if extraction fails
            else:
                print(
                    f"[{self.name}] Error: Directory {data_dir} does not exist and {zip_file_path} not found."
                )
                print(
                    f"[{self.name}] Task aborted. Please ensure data is present in {data_dir} or {zip_file_path} exists."
                )
                return None  # Exit if neither directory nor zip file is found
        return data_dir

    def execute(self) -> None:
        # STEP 1: Find out where the sensor data files are stored on the computer.
        data_dir = self._ensure_data_ready()
        if data_dir is None:
            return  # Abort if data directory could not be prepared
        # STEP 2: The "Cheat Sheet". These are the normal, safe ranges for each sensor.
        sensor_ranges = {
            "temperature": {"key": "temperature_K", "min": 553.0, "max": 873.0},
            "pressure": {"key": "pressure_bar", "min": 60.0, "max": 160.0},
            "water": {"key": "water_level_meters", "min": 5.0, "max": 15.0},
            "voltage": {"key": "voltage_supply_v", "min": 229.0, "max": 231.0},
            "humidity": {"key": "humidity_percent", "min": 40.0, "max": 80.0},
        }

        # anomalies will hold the IDs (filenames) of all the bad files we find.
        anomalies = []
        # valid_files_by_note will group all the good files by their exact human note.
        valid_files_by_note = {}

        print(f"[{self.name}] Programmatically analyzing sensor files...")

        # STEP 3: Grab all the .json files from the folder
        json_files = []
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file.endswith(".json"):
                    json_files.append(os.path.join(root, file))

        # STEP 4: The Fast Check. Open every file and check the numbers!
        for file_path in json_files:
            filename = os.path.basename(file_path)
            with open(file_path, "r") as f:
                data = json.load(f)

            sensor_type_str = data.get("sensor_type", "")
            active_sensors = set(sensor_type_str.split("/"))

            is_valid = True
            for sensor_name, config in sensor_ranges.items():
                val = data.get(config["key"], 0)
                if sensor_name in active_sensors:
                    if not (config["min"] <= val <= config["max"]):
                        is_valid = False
                        break
                else:
                    if val != 0:
                        is_valid = False
                        break

            file_id = filename.replace(".json", "")

            if not is_valid:
                anomalies.append(file_id)
            else:
                note = data.get("operator_notes", "")
                if note not in valid_files_by_note:
                    valid_files_by_note[note] = []
                valid_files_by_note[note].append(file_id)

        print(f"[{self.name}] Found {len(anomalies)} files with invalid measurements.")

        unique_notes = list(valid_files_by_note.keys())
        print(
            f"[{self.name}] Found {len(unique_notes)} unique operator notes from valid files."
        )

        note_dict = {str(i): note for i, note in enumerate(unique_notes)}
        batch_size = 500
        problematic_note_ids = []

        print(f"[{self.name}] Sending notes to LLM in batches of {batch_size}...")

        # STEP 5: The AI Check. Send the unique notes to the AI in chunks (batches).
        for i in range(0, len(unique_notes), batch_size):
            batch = {
                k: note_dict[k] for k in list(note_dict.keys())[i : i + batch_size]
            }

            prompt = f"""You are an AI assistant analyzing operator notes from a power plant.
For each note, determine if the operator is reporting a problem, error, anomaly, or required intervention.
Return ONLY a valid JSON list of IDs (strings) for the notes that indicate a problem. Do not wrap the response in markdown blocks. Return a raw JSON array.
If no notes indicate a problem, return an empty list [].

Input:
{json.dumps(batch)}
"""
            try:
                batch_anomalies = self._evaluate_batch_with_llm(prompt)
                problematic_note_ids.extend(batch_anomalies)
                print(
                    f"[{self.name}] Batch {i//batch_size + 1}: Found {len(batch_anomalies)} problematic notes."
                )
            except Exception as e:
                print(f"[{self.name}] Error analyzing batch {i//batch_size + 1}: {e}")

        # STEP 6: Combine the results.
        for note_id in problematic_note_ids:
            if note_id in note_dict:
                note_text = note_dict[note_id]
                files_with_note = valid_files_by_note[note_text]
                anomalies.extend(files_with_note)

        print(f"[{self.name}] Total anomalies found: {len(anomalies)}")

        # STEP 7: The Final Report.
        print(f"[{self.name}] Sending verification request...")
        verify_data = {"recheck": anomalies}
        response = verify_answer("evaluation", verify_data)
        print(f"[{self.name}] Verification Response: {response}")

        # Flush events to ensure all logs are sent to the Langfuse server before the script exits
        langfuse.flush()


def run_task11_evaluation(agent_model):
    shared_agent = Agent(default_model=agent_model)

    orchestrator = AgentOrchestrator()
    orchestrator.add_task(
        SensorEvaluationTask(
            name="SensorEvaluation", agent=shared_agent, memory=orchestrator.memory
        )
    )

    orchestrator.run()

    shared_agent.print_usage_statistics()


if __name__ == "__main__":
    run_task11_evaluation("google/gemini-3-flash-preview")
