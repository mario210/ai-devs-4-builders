import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from ai.memory import SharedMemory
from task.task20_foodwarehouse_v2.foodwarehouse_task import FoodWarehouseTask

load_dotenv()

AGENT_MODEL = "google/gemini-3.1-pro-preview"
TASK_NAME = "foodwarehouse"


def food_warehouse_orchestrator():
    agent = Agent(default_model=AGENT_MODEL)
    memory = SharedMemory()
    orchestrator = AgentOrchestrator()

    memory.set("task_name", TASK_NAME)

    orchestrator.add_task(FoodWarehouseTask(agent=agent, memory=memory))
    orchestrator.run()


if __name__ == "__main__":
    food_warehouse_orchestrator()
