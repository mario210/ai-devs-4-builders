import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
from loguru import logger
import argparse

from ai.agent import Agent
from ai.tools.hub_requests import verify_answer
from task.task2_findhim.task2_tools import TOOLS_SEARCH, TOOLS_SEARCH_MAP

# --- Constants ---
USER_PROMPT = """Find the person who was closest to the power plant and then check their access level.
Your response MUST be only the JSON object itself, without any additional text, explanations, or markdown code blocks.
Example JSON: {"name": "John", "surname": "Doe", "accessLevel": 1, "powerPlant": "examplePP"}"""


def run_task2_findhim(agent_model: str) -> None:
    """
    Runs the 'FindHim' task.

    This task involves:
    1. Initializing an AI agent.
    2. Prompting the agent to find a person based on specific criteria.
    3. Parsing the agent's JSON response.
    4. Verifying the answer with an external service.
    5. Logging the final result.

    Args:
        agent_model: The identifier for the AI model to use (e.g., "openai/gpt-4o-mini").
    """
    logger.info(
        "--- Running Task 2: FindHim (Search for person and get access level) ---"
    )

    try:
        agent = Agent(default_model=agent_model)
        logger.info(f"USER: {USER_PROMPT}")

        messages = [{"role": "user", "content": USER_PROMPT}]
        final_answer = agent.chat(
            messages, tools=TOOLS_SEARCH, tool_map=TOOLS_SEARCH_MAP
        )
        logger.info(f"LLM: {final_answer}")

        answer_payload = json.loads(final_answer)

    except json.JSONDecodeError:
        logger.error(
            "Agent's response is not valid JSON. Cannot proceed with verification."
        )
        logger.error(f"Received response: '{final_answer}'")
        return
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during agent interaction: {e}", exc_info=True
        )
        return

    verify_answer("findhim", answer_payload)


def main() -> None:
    """Main function to run the task from the command line."""
    parser = argparse.ArgumentParser(description="Run the FindHim task.")
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-4o-mini",
        help="The AI model to use for the agent.",
    )
    args = parser.parse_args()

    run_task2_findhim(agent_model=args.model)


if __name__ == "__main__":
    main()
