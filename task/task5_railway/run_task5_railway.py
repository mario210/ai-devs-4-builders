import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ai.agent import Agent
from ai.tools import definition
from task.task5_railway.task5_tools import RAILWAY_TOOLS, RAILWAY_TOOLS_MAP
from pathlib import Path


# --- Task 5: Railway ---
def run_task5_railway():
    print("\n--- Running Task 5: Railway (Activate the route) ---")
    agent = Agent()

    # Combine tools
    tools = []
    tools.extend(definition.DOCUMENT_CRAWLER_TOOLS)
    tools.extend(RAILWAY_TOOLS)

    tool_map = {**definition.DOCUMENT_CRAWLER_TOOLS_MAP, **RAILWAY_TOOLS_MAP}

    user_prompt = (
        Path(__file__)
        .parent.parent.parent.joinpath("task", "task5_railway/task5_railway.md")
        .read_text(encoding="utf-8")
    )
    final_answer = agent.chat(
        messages=[{"role": "user", "content": user_prompt}],
        tools=tools,
        tool_map=tool_map,
        max_iterations=20,
    )
    print(final_answer)


if __name__ == "__main__":
    run_task5_railway()
