import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from task.task18_domatowo.agents.map_analyst_agent import MapAnalystAgent
from task.task18_domatowo.agents.logistician_agent import LogisticianAgent
from task.task18_domatowo.agents.field_commander_agent import FieldCommanderAgent
from task.task18_domatowo.agents.log_analyst_agent import LogAnalystAgent
from task.task18_domatowo.agents.evacuation_agent import EvacuationAgent

from ai.tools.hub_requests import verify_answer

# Load environment variables from .env file
load_dotenv()


def domatowo_rescue_plan_orchestrator():
    task_name = "domatowo"

    # Get API documentation once
    help_response = verify_answer(task_name, {"action": "help"})

    # Reset the task at the beginning of each attempt
    verify_answer(task_name, {"action": "reset"})

    # Create the agent model and orchestrator
    agent_model = Agent()
    orchestrator = AgentOrchestrator()
    memory = orchestrator.memory

    # Initialize shared memory
    memory.set("task_name", task_name)
    memory.set("partisan_found", False)
    memory.set("partisan_coordinates", None)
    memory.set("api_documentation", help_response)

    # Add tasks (agents) to the orchestrator

    # 1. Analyzes geographical data and maps to identify key locations or routes.
    orchestrator.add_task(MapAnalystAgent(agent_model=agent_model, memory=memory))

    # 2. Focuses on resource management, supply chains, and safe movement planning.
    orchestrator.add_task(LogisticianAgent(agent_model=agent_model, memory=memory))

    # 3. Commands field operations, makes tactical decisions, and coordinates ground movements.
    orchestrator.add_task(FieldCommanderAgent(agent_model=agent_model, memory=memory))

    # 4. Processes system logs, sensor data, or communication records to gather intelligence.
    orchestrator.add_task(LogAnalystAgent(agent_model=agent_model, memory=memory))

    # 5. Plans and executes the final extraction and safe evacuation of the target.
    orchestrator.add_task(EvacuationAgent(agent_model=agent_model, memory=memory))

    orchestrator.run()


if __name__ == "__main__":
    domatowo_rescue_plan_orchestrator()
