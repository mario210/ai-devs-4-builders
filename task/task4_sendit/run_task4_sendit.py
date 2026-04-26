import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ai.agent import Agent
from ai.tools import definition
from pathlib import Path


# --- Task 4: Sendit ---
def run_task4_sendit():
    print("\n--- Running Task 4: Sendit (Transport declaration) ---")
    agent = Agent()

    # Adjust path for the new location:
    user_prompt = (
        Path(__file__)
        .parent.parent.parent.joinpath("task", "task4_sendit/task4_sendit.md")
        .read_text(encoding="utf-8")
    )

    messages = [{"role": "user", "content": user_prompt}]
    final_answer = agent.chat(
        messages, tools=definition.ALL_AGENT_TOOlS, tool_map=definition.ALL_TOOL_MAP
    )
    print(final_answer)


if __name__ == "__main__":
    run_task4_sendit()
