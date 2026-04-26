import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from ai.agents.file_reader_agent import read_file_content
from task.task19_filesystem.agents.natan_notes_agent import NatanNotesAgent
from task.task19_filesystem.agents.file_system_builder_agent import (
    FileSystemBuilderAgent,
)

from ai.tools.hub_requests import verify_answer

# Load environment variables from .env file
load_dotenv()

TASK_NAME = "filesystem"


def natan_notes_orchestrator():

    # Reset the task at the beginning of each attempt
    verify_answer(TASK_NAME, {"action": "reset"})

    # Get API documentation once
    help_response = verify_answer(TASK_NAME, {"action": "help"})

    # Create the agent model and orchestrator
    agent_model = Agent(default_model="openai/gpt-5.4")
    orchestrator = AgentOrchestrator()
    memory = orchestrator.memory

    # Initialize shared memory
    memory.set("task_name", TASK_NAME)
    memory.set("api_documentation", help_response)

    # Read text files into memory
    files = [
        ("rozmowy.txt", "rozmowy_contents"),
        ("transakcje.txt", "transakcje_contents"),
        ("ogłoszenia.txt", "ogloszenia_contents"),
    ]
    for filename, key in files:
        contents = read_file_content(f"../../data/natan_notes/{filename}")
        memory.set(key, contents)

    orchestrator.add_task(NatanNotesAgent(agent_model, memory))
    orchestrator.add_task(FileSystemBuilderAgent(agent_model, memory))
    orchestrator.run()


if __name__ == "__main__":
    natan_notes_orchestrator()
    final_response = verify_answer(TASK_NAME, {"action": "done"})
