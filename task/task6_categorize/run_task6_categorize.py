import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
from dotenv import load_dotenv
from ai.agent import Agent, AGENTS_API_KEY
from ai.tools import definition
from task.task6_categorize.task6_tools import submit_categorization
from ai.tools.hub_requests import verify_answer
import csv
import json
import time

# Load environment variables
load_dotenv()

VERIFY_API_URL = os.environ.get("HUB_API_VERIFY_URL")


# --- Task 6: Categorize ---
def run_task6_categorize(agent_model):
    print("\n--- Running Task 6: Categorize ---")
    agent = Agent(default_model=agent_model, use_cache=True)

    # 1. Fetch the data
    hub_data_url = os.environ.get("HUB_DATA_BASE_URL")
    url = f"{hub_data_url}/{AGENTS_API_KEY}/categorize.csv"
    messages = [
        {
            "role": "user",
            "content": f"Fetches a CSV file from a provided {url} and returns its raw text content. Do not parse the file. Do not add any comments to the output.",
        }
    ]
    csv_content = agent.chat(
        messages,
        tools=definition.DOCUMENT_CRAWLER_TOOLS,
        tool_map=definition.DOCUMENT_CRAWLER_TOOLS_MAP,
    )

    # Check for immediate errors from the ai.chat call
    if not csv_content:
        print("Failed to fetch CSV data: Agent returned empty response.")
        return
    if isinstance(csv_content, str) and "Error" in csv_content:
        print(f"Failed to fetch CSV data: {csv_content}")
        return
    # If it's a dict and has an 'error' key, treat it as an error
    if isinstance(csv_content, dict) and "error" in csv_content:
        print(f"Failed to fetch CSV data: {csv_content['error']}")
        return

    print("--- CSV DATA START ---")
    print(csv_content)
    print("--- CSV DATA END ---")

    # 2. Process fetched data (now expected to be a list of dictionaries)
    try:
        lines = csv_content.strip().splitlines()
        reader = csv.reader(lines)
        next(reader)  # Skip header
        items_to_classify = {row[0]: row[1] for row in reader if len(row) == 2}
    except (csv.Error, StopIteration, IndexError) as e:
        print(f"Error processing CSV text data: {e}")
        return

    # 4. & 5. Iterative Classification with Learning and Reset Loop
    # The base prompt should be concise. Dynamic additions will be appended based on errors.
    base_classification_prompt = "Classify item as DNG or NEU. Reactor parts are always NEU, regardless of the item description."

    # State trackers
    successfully_classified_ids = set()
    permanently_failed_items = set()
    item_prompts = {
        item_id: base_classification_prompt for item_id in items_to_classify.keys()
    }
    max_retries_per_item = 5
    max_task_attempts = 5  # Max number of times we will reset the balance

    for task_attempt in range(max_task_attempts):
        print(
            f"\n--- Starting Full Task Attempt #{task_attempt + 1}/{max_task_attempts} ---"
        )
        # Reset token budget at the start of each major attempt.
        print("Resetting token budget...")
        reset_response = verify_answer("categorize", {"prompt": "reset"})

        print(f"Reset response: {reset_response}")

        funds_error_in_this_pass = False

        # Try to classify all items, with retries for each item.
        for item_id, item_description in items_to_classify.items():
            # Skip items that have already been successfully classified or have permanently failed
            if (
                item_id in successfully_classified_ids
                or item_id in permanently_failed_items
            ):
                continue

            item_specific_prompt = item_prompts[item_id]
            success_for_this_item = False

            for attempt in range(max_retries_per_item):
                full_prompt = f"{item_specific_prompt} ID: {item_id}, Description: {item_description}"
                print(
                    f"\n--- Attempt {attempt + 1}/{max_retries_per_item} for ID: {item_id} ---"
                )

                submission_response = submit_categorization({"prompt": full_prompt})
                # print(f"Hub Response: {submission_response}")

                # If the response is a JSON string, try to parse it
                # If it's a string but not JSON, treat it as an error message directly
                if isinstance(submission_response, str):
                    try:
                        submission_response = json.loads(submission_response)
                    except json.JSONDecodeError:
                        submission_response = {"code": 1, "error": submission_response}

                # submission_response is expected to be a dict now
                if isinstance(submission_response, dict):
                    # Check for a global success signal (code: 0) which means the entire task is done.
                    if submission_response.get("code") == 0:
                        print("\n--- Global Success Signal (code: 0) Received ---")
                        print(
                            "Server indicates the entire categorization task is complete."
                        )
                        print(
                            "\n--- Script finished. All items categorized successfully. ---"
                        )
                        return  # Exit the function immediately

                    if submission_response.get("message") == "ACCEPTED":
                        print(f"OK. ID {item_id} classified successfully.")
                        success_for_this_item = True
                        successfully_classified_ids.add(item_id)
                        break  # Success, break from retry loop for this item
                    else:
                        # ERROR: Learn, adjust prompt, and retry this item.

                        # First, check for a catastrophic funds error that requires a full reset.
                        top_level_message = submission_response.get("error", {})
                        if (
                            isinstance(top_level_message, str)
                            and "insufficient funds" in top_level_message.lower()
                        ):
                            print(f"FATAL ERROR for ID {item_id}: {top_level_message}")
                            print(
                                "This requires a full task reset. Will restart and re-check ALL items."
                            )
                            funds_error_in_this_pass = True
                            break  # Break from the per-item retry loop. The outer loops will handle the reset.

                        # The detailed error might be a JSON string inside the 'error' key.
                        # We need to find the dictionary that contains the actual error details.
                        error_details_source = submission_response
                        error_content = submission_response.get("error")

                        if isinstance(error_content, str):
                            try:
                                # Try to parse the string value of 'error' as JSON
                                parsed_error = json.loads(error_content)
                                # If it's a dict, we assume this is our new source of truth
                                if isinstance(parsed_error, dict):
                                    error_details_source = parsed_error
                                    # print("Info: Parsed detailed error from the 'error' field string.")
                            except json.JSONDecodeError:
                                print(
                                    f"Warning: The 'error' field contained a string that was not valid JSON: {error_content}"
                                )

                        debug_info = error_details_source.get("debug", {})
                        error_reason = debug_info.get("result")
                        error_output = debug_info.get("output")

                        if error_reason and error_output:
                            print(
                                f"Classification FAILED for ID {item_id}. Reason: '{error_reason}', Output was: '{error_output}'"
                            )
                            # Learn from both 'result' and 'output' to refine the prompt for the next retry.
                            new_instruction = f"Hint: The output '{error_output}' was a '{error_reason}'. Reclassify."
                            item_specific_prompt += f" {new_instruction}"
                            item_prompts[item_id] = (
                                item_specific_prompt  # Save learned prompt
                            )
                            print(
                                "Learning from error. Will retry this item with an updated prompt."
                            )

                        elif error_reason:
                            print(
                                f"Classification FAILED for ID {item_id}. Reason from 'result' field: '{error_reason}'"
                            )
                            # Fallback to learning from 'result' only
                            new_instruction = f"Hint: A previous attempt was a '{error_reason}'. Reclassify."
                            item_specific_prompt += f" {new_instruction}"
                            item_prompts[item_id] = (
                                item_specific_prompt  # Save learned prompt
                            )
                            print(
                                "Learning from error. Will retry this item with an updated prompt."
                            )
                        else:
                            print(
                                f"Classification FAILED for ID {item_id}, but no specific 'result' field found to learn from. Full response: {submission_response}"
                            )
                            print(
                                "Cannot learn from this error. Will retry with the same prompt after a delay."
                            )

                        time.sleep(2)
                        # Loop will continue to the next attempt for this item with the (potentially) updated prompt
                else:
                    print(
                        f"Unexpected response format for ID {item_id}. Aborting retries for this item."
                    )
                    break  # Break from the retry loop for this item

            if funds_error_in_this_pass:
                break  # Break from the main item loop to restart the whole task

            if not success_for_this_item:
                # If we exhausted retries for a non-funds error, mark it as permanently failed
                print(
                    f"--- FAILED to classify ID {item_id} after {max_retries_per_item} attempts. ---"
                )
                permanently_failed_items.add(item_id)

        # After iterating through all items...
        if not funds_error_in_this_pass:
            # If we completed a full pass without a funds error, we're done. No need for more task attempts.
            print("\nCompleted a full pass without encountering a funds error.")
            break  # Break from the outer task_attempt loop
        else:
            # A funds error occurred, the outer loop will now start the next task_attempt
            print(
                "Clearing all progress due to funds error. All items will be re-checked on the next attempt."
            )
            successfully_classified_ids.clear()
            permanently_failed_items.clear()

            if not items_to_classify:
                print(
                    "Funds error occurred, but there are no items to process. Exiting task."
                )
                break
            print(
                f"Restarting task attempt due to funds error. {len(items_to_classify)} items will be re-checked."
            )

    # Final reporting
    final_failed_set = set(items_to_classify.keys()) - successfully_classified_ids

    if not final_failed_set:
        print("\n--- Script finished. All items categorized successfully. ---")
    else:
        print(
            f"\n--- Script finished. FAILED to classify the following items: {sorted(list(final_failed_set))} ---"
        )


if __name__ == "__main__":
    run_task6_categorize("anthropic/claude-sonnet-4-6")
