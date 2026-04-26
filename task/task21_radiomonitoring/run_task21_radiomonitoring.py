import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from ai.memory import SharedMemory
from task.task21_radiomonitoring.radiomonitoring_listener_task import (
    RadiomonitoringListenerTask,
)
from ai.tools.hub_requests import verify_answer

load_dotenv()

# AGENT_MODEL = "openai/gpt-4o-mini"
# AGENT_MODEL = "openai/gpt-5.4"
AGENT_MODEL = "google/gemini-3.1-pro-preview"
TASK_NAME = "radiomonitoring"


def radio_monitoring_agentic_orchestrator():
    agent = Agent(default_model=AGENT_MODEL)
    memory = SharedMemory()
    orchestrator = AgentOrchestrator()
    memory.set("task_name", TASK_NAME)

    # start session
    verify_answer(TASK_NAME, {"action": "start"})

    # The RadiomonitoringListenerTask handles the action: listen loop
    orchestrator.add_task(RadiomonitoringListenerTask(agent=agent, memory=memory))
    orchestrator.run()

    findings = memory.get("radio_findings")
    if findings:
        print(f"Submitting findings to HQ: {findings}")

        payload = {
            "action": "transmit",
            "cityName": findings.get("cityName"),
            "cityArea": findings.get("cityArea"),
            "warehousesCount": findings.get("warehousesCount"),
            "phoneNumber": findings.get("phoneNumber"),
        }
        verify_answer(TASK_NAME, payload)
    else:
        print("No findings were extracted from the radio monitoring task.")


if __name__ == "__main__":
    radio_monitoring_agentic_orchestrator()
