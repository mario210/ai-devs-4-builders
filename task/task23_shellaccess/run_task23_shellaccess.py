import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from ai.memory import SharedMemory
from task.task23_shellaccess.shellaccess_task import ShellAccessTask

load_dotenv()


AGENT_MODEL = "anthropic/claude-opus-4.6"
# AGENT_MODEL = "openai/gpt-5.4"
# AGENT_MODEL = "google/gemini-3.1-pro-preview"
# AGENT_MODEL = "openai/gpt-4o-mini"
# AGENT_MODEL = "openai/gpt-5-nano"
TASK_NAME = "shellaccess"


def shellaccess_orchestrator():
    agent = Agent(default_model=AGENT_MODEL)
    memory = SharedMemory()
    orchestrator = AgentOrchestrator()
    memory.set("task_name", TASK_NAME)
    orchestrator.add_task(ShellAccessTask(agent_model=agent, memory=memory))
    orchestrator.run()


if __name__ == "__main__":
    shellaccess_orchestrator()
