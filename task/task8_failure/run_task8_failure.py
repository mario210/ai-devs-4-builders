import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
from ai.agent import Agent
from ai.tools.hub_requests import verify_answer
from task.task8_failure.task8_tools import filter_logs


def run_task8_failure(agent_model):
    print(
        "\n--- Running Task 8: Failure (Deterministic Filtering + LLM Compression) ---"
    )

    log_filepath = "../../data/failure.log"
    if not os.path.exists(log_filepath):
        print(
            f"Error: Log file not found at {log_filepath}. Please ensure it is downloaded."
        )
        return

    print("--- Filtering logs to get the last 5 of each critical level ---")

    # 1. Filter logs using the new precise logic
    filtered_content = filter_logs(log_path=log_filepath)

    # 2. Use an LLM Agent to compress the filtered logs
    print("--- Compressing filtered logs using LLM ---")
    compressor_agent = Agent(default_model=agent_model)

    compression_prompt = f"""You are an expert log compression specialist. Your task is to aggressively shorten the following log entries to fit under a strict character limit, while preserving the most critical information.

        **CRITICAL GOAL: The total length of your final output MUST be less than 1500 characters.**

        Rules:
        1.  **MUST** keep the original date and timestamp for every line.
        2.  **REMOVE** the log level (e.g., `[CRIT]`, `[ERRO]`, `[WARN]`). It should not be in the output.
        3.  **MUST** keep all system identifiers (e.g., ECCS8, WTANK07, PWR01, FIRMWARE, STMTURB12, WTRPMP).
        4.  Aggressively rephrase and shorten the descriptive text. Use abbreviations (e.g., 'temperature' -> 'temp', 'exceeded' -> '>').
        5.  If you are still over the character limit, you may remove the least important log entries to meet the goal.
        6.  Do not add any commentary or explanation. Return only the compressed log lines.

        Example of good compression:
        - Original: `[2026-03-17 06:36:40] [ERRO] WTANK07 indicates unstable refill trend. Available coolant inventory is no longer guaranteed.`
        - Compressed: `[2026-03-17 06:36:40] WTANK07 unstable refill, coolant not guaranteed.`

        Here are the logs to compress:
        ---
        {filtered_content}
        ---
    """

    # This ai just needs to reason and return text, no tools needed.
    compressed_result = compressor_agent.chat(
        messages=[{"role": "user", "content": compression_prompt}], max_iterations=1
    )

    print(f"Final compressed log length: {len(compressed_result)}")
    print("Final log content to be sent for verification:\n" + compressed_result)

    # 3. Verify the result
    verify_response = verify_answer("failure", {"logs": compressed_result})

    code = verify_response.get("code") if isinstance(verify_response, dict) else None

    if code == 0:
        print("Success! Verification passed.")
    else:
        error_msg = verify_response.get("message", str(verify_response))
        print(f"Verification failed. Feedback: {error_msg}")
        print(
            "If this failed, the compression prompt or the filtering logic in 'filter_logs' may need to be adjusted based on the feedback."
        )


if __name__ == "__main__":
    run_task8_failure("openai/gpt-5-mini")
