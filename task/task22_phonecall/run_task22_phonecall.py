import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from ai.memory import SharedMemory
from task.task22_phonecall.phonecall_task import PhoneCallTask

load_dotenv()

AGENT_MODEL = "anthropic/claude-sonnet-4.6"
TASK_NAME = "phonecall"


def phonecall_orchestrator():
    agent = Agent(default_model=AGENT_MODEL)
    memory = SharedMemory()
    orchestrator = AgentOrchestrator()
    memory.set("task_name", TASK_NAME)
    orchestrator.add_task(PhoneCallTask(agent_model=agent, memory=memory))
    orchestrator.run()


if __name__ == "__main__":
    phonecall_orchestrator()
