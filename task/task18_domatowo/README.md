# Domatowo Rescue Plan

This module is responsible for orchestrating a multi-agent AI system designed to execute a rescue mission in the "Domatowo" scenario. 

## How `domatowo_rescue_plan_orchestrator` Works

The `domatowo_rescue_plan_orchestrator` function serves as the central brain of the task. It initializes the environment, manages shared state (memory), and schedules specialized AI agents to work together to achieve the rescue goal.

### 1. Pre-Task Setup & API Initialization
When the orchestrator starts, it performs a few crucial setup steps:
- **Fetch Documentation:** It queries the central hub (`verify_answer`) with a `"help"` action to fetch the latest API documentation. This ensures agents know how to interact with the environment.
- **Reset State:** It sends a `"reset"` action to guarantee the scenario begins from a clean slate on every attempt.

### 2. Orchestrator & Memory Instantiation
- It creates the underlying AI model (`agent_model`) and an `AgentOrchestrator`.
- **Shared Memory:** A shared memory space is initialized to act as a central whiteboard for the agents. It stores:
  - `task_name`: The current scenario ("domatowo").
  - `partisan_found`: A boolean tracker indicating if the missing partisan has been located.
  - `partisan_coordinates`: The exact location of the target once found.
  - `api_documentation`: The instructions fetched during the setup phase, so agents know the rules of engagement.

### 3. The Agent Pipeline
The orchestrator adds several specialized agents to the pipeline. Because they share the same memory, discoveries made by one agent seamlessly cascade to the next:

1. **Map Analyst Agent:** Analyzes spatial and geographical data to understand the terrain of Domatowo.
2. **Logistician Agent:** Handles supply routes, movement feasibility, and operational constraints based on the map data.
3. **Field Commander Agent:** Uses the logistics and map intelligence to make tactical decisions and maneuver virtual assets in the field.
4. **Log Analyst Agent:** Scours server logs, communications, or environmental sensors for specific clues (which likely leads to discovering the `partisan_coordinates`).
5. **Evacuation Agent:** Steps in once the target is located to finalize the extraction routing and complete the mission.

### 4. Execution
Finally, `orchestrator.run()` is called. This triggers the sequential (or managed) execution of the agents, allowing them to collaborate, update the shared memory, and ultimately execute the Domatowo rescue plan.