import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from ai.memory import SharedMemory
from task.task25_timetravel.timetravel_api_agent import TimetravelApiAgent
from ai.tools.hub_requests import verify_answer

load_dotenv()

AGENT_MODEL = "openai/gpt-5.4"
TASK_NAME = "timetravel"


def timetravel_agentic_orchestrator():
    agent = Agent(default_model=AGENT_MODEL)
    memory = SharedMemory()
    orchestrator = AgentOrchestrator()
    memory.set("task_name", TASK_NAME)

    api_task = TimetravelApiAgent(agent=agent, memory=memory)

    # The Orchestrator runs the API agent task
    orchestrator.add_task(api_task)

    orchestrator.run()


if __name__ == "__main__":
    # reset time machine state
    verify_answer(TASK_NAME, {"action": "reset"})

    timetravel_agentic_orchestrator()
