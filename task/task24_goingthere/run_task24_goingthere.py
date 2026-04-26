import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from ai.memory import SharedMemory
from task.task24_goingthere.goingthere_task import MissionCommander  # Updated import

load_dotenv()


# AGENT_MODEL = "google/gemma-4-26b-a4b-it:free"
# AGENT_MODEL = "anthropic/claude-opus-4.6"
# AGENT_MODEL = "anthropic/claude-sonnet-4.6"
# AGENT_MODEL = "openai/gpt-4o-mini"
AGENT_MODEL = "openai/gpt-5.4"
# AGENT_MODEL = "google/gemini-3.1-pro-preview"
TASK_NAME = "goingthere"


def going_there_orchestrator():
    agent = Agent(default_model=AGENT_MODEL)
    memory = SharedMemory()
    orchestrator = AgentOrchestrator()
    memory.set("task_name", TASK_NAME)
    orchestrator.add_task(MissionCommander(agent_model=agent, memory=memory))
    orchestrator.run()


if __name__ == "__main__":
    going_there_orchestrator()
