import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from ai.orchestrator import AgentOrchestrator
from ai.agent import Agent
from task.task17_windpower.agents.documentation_agent import DocumentationAgent
from task.task17_windpower.agents.weather_agent import WeatherAgent
from task.task17_windpower.agents.power_plant_agent import PowerPlantAgent
from task.task17_windpower.agents.turbine_agent import TurbineAgent
from task.task17_windpower.agents.results_polling_agent import ResultsPollingAgent
from task.task17_windpower.agents.config_generator_agent import ConfigGeneratorAgent
from task.task17_windpower.agents.config_applier_agent import ConfigApplierAgent
from task.task17_windpower.agents.final_validation_agent import FinalValidationAgent
from ai.tools.hub_requests import verify_answer

# Load environment variables from .env file
load_dotenv()


def windpower_orchestrator():
    task_name = "windpower"

    # Start the task
    verify_answer(task_name, {"action": "start"})

    # Create the agent model and orchestrator
    agent_model = Agent(default_model="google/gemini-3.1-pro-preview")
    orchestrator = AgentOrchestrator(main_agent=agent_model)
    memory = orchestrator.memory

    # Initialize shared memory
    memory.set("task_name", task_name)
    memory.set(
        "expected_results_count",
        {"forecast": 1, "powerplant": 1, "turbine_status": 1, "unlockCodeGenerator": 0},
    )
    memory.set("unlockCodeGenerator_map", {})

    # Add tasks (agents) to the orchestrator
    orchestrator.add_task(DocumentationAgent(agent_model=agent_model, memory=memory))
    orchestrator.add_task(WeatherAgent(agent_model=agent_model, memory=memory))
    orchestrator.add_task(PowerPlantAgent(agent_model=agent_model, memory=memory))
    orchestrator.add_task(TurbineAgent(agent_model=agent_model, memory=memory))
    orchestrator.add_task(ResultsPollingAgent(agent_model=agent_model, memory=memory))
    orchestrator.add_task(ConfigGeneratorAgent(agent_model=agent_model, memory=memory))
    orchestrator.add_task(
        ResultsPollingAgent(agent_model=agent_model, memory=memory)
    )  # Poll for unlock codes
    orchestrator.add_task(ConfigApplierAgent(agent_model=agent_model, memory=memory))
    orchestrator.add_task(FinalValidationAgent(agent_model=agent_model, memory=memory))

    # Run the workflow
    orchestrator.run()


if __name__ == "__main__":
    windpower_orchestrator()
