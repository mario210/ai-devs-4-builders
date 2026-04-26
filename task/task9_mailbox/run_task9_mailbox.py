import sys
import os
import time
import json
from ai.agent import Agent
from ai.tools.hub_requests import verify_answer
from task.task9_mailbox.task9_tools import (
    mail_check_available_actions,
    mail_search,
    mail_get_content_by_id,
)

# Add the current directory to sys.path to find local modules
sys.path.append(os.path.dirname(__file__))


def run_task9_mailbox(agent_model):
    print("\n--- Running Task 9: Mailbox ---")

    # Initialize the Agent correctly
    agent = Agent(default_model=agent_model)

    extracted_date = None
    extracted_password = None
    extracted_confirmation_code = None
    all_email_contents = []
    seen_email_ids = set()

    # Step 1: Check available actions (optional, but good for understanding API)
    print("Checking available mailbox actions...")
    available_actions = mail_check_available_actions()
    print(f"Available actions: {available_actions}")

    # Step 2: Manually perform the search loop to avoid LLM ai stopping prematurely
    print("Searching for relevant emails using mail_search...")

    # We use a set of variations for the sender
    search_queries = [
        "from:vik4tor@proton.me",
        "to:vik4tor@proton.me",
        "PWR6132PL",
        "password",
        "hasło",
        "kod",
        "code",
    ]

    polling_iteration = 0
    max_polling_iterations = 20

    while (
        not (extracted_date and extracted_password and extracted_confirmation_code)
        and polling_iteration < max_polling_iterations
    ):
        polling_iteration += 1
        print(f"\n--- Search Polling Iteration {polling_iteration} ---")

        new_emails_found = False

        for query in search_queries:
            print(f"Searching with query: {query}")
            search_response = mail_search(query=query)

            if search_response and search_response.get("ok"):
                items = search_response.get("items", [])
                if items:
                    for item in items:
                        mail_id = item.get("messageID")
                        if mail_id and mail_id not in seen_email_ids:
                            print(
                                f"Found new email matching query '{query}'. Retrieving content for email ID: {mail_id}"
                            )
                            content_response = mail_get_content_by_id(mail_id=mail_id)
                            if content_response:
                                all_email_contents.append(
                                    json.dumps(content_response, ensure_ascii=False)
                                )
                                seen_email_ids.add(mail_id)
                                new_emails_found = True
                                print(f"  Added content from email ID {mail_id}")
            else:
                print(f"Search failed or returned no results for query '{query}'")

        if new_emails_found or all_email_contents:
            print(
                f"\nCollected {len(all_email_contents)} email contents so far. Attempting extraction..."
            )

            # Step 3: Prepare message for LLM to extract information
            extraction_prompt = (
                "You are an expert email analyst. Below are the contents of several emails. "
                "Your task is to extract three specific pieces of information from these emails:\n"
                "1. `date`: The date (format YYYY-MM-DD) when the security department plans an attack.\n"
                "2. `password`: The password to the employee system.\n"
                "3. `confirmation_code`: A confirmation code from a security department ticket, "
                "which will be in the format `SEC-` followed by 32 characters (total 36 characters).\n\n"
                "Please provide the extracted information in a JSON object with the keys `date`, `password`, "
                "and `confirmation_code`. If a piece of information is not found yet, use `null` for its value. "
                "Make sure to retain previously found values if you find new ones.\n\n"
                f"Currently extracted:\nDate: {extracted_date}\nPassword: {extracted_password}\nConfirmation Code: {extracted_confirmation_code}\n\n"
                "Email Contents:\n" + "\n---\n".join(all_email_contents)
            )

            extraction_messages = [{"role": "user", "content": extraction_prompt}]

            print("\nSending collected email contents to LLM for extraction...")
            llm_response = agent.chat(extraction_messages, model=agent_model)

            if llm_response:
                print("\nLLM Response for extraction:")
                print(llm_response)
                try:
                    # Attempt to clean the LLM response if it includes markdown or other text
                    cleaned_response = str(llm_response)
                    if cleaned_response.startswith(
                        "```json"
                    ) and cleaned_response.endswith("```"):
                        cleaned_response = cleaned_response[7:-3].strip()
                    elif cleaned_response.startswith(
                        "```"
                    ) and cleaned_response.endswith("```"):
                        cleaned_response = cleaned_response[3:-3].strip()

                    extracted_data = json.loads(cleaned_response)

                    if extracted_data.get("date"):
                        extracted_date = extracted_data.get("date")
                    if extracted_data.get("password"):
                        extracted_password = extracted_data.get("password")
                    if extracted_data.get("confirmation_code"):
                        extracted_confirmation_code = extracted_data.get(
                            "confirmation_code"
                        )

                    print(f"Extracted Date: {extracted_date}")
                    print(f"Extracted Password: {extracted_password}")
                    print(f"Extracted Confirmation Code: {extracted_confirmation_code}")
                except json.JSONDecodeError:
                    print("Failed to parse LLM response as JSON.")
                    print(f"Raw LLM response: {llm_response}")
            else:
                print("LLM did not return a response for extraction.")

        if not (extracted_date and extracted_password and extracted_confirmation_code):
            print(
                "Not all information found yet. Waiting 8 seconds before polling again..."
            )
            time.sleep(8)

    if not (extracted_date and extracted_password and extracted_confirmation_code):
        print("Failed to collect all necessary information after maximum iterations.")
        return

    # Final verification request if all data is extracted
    if extracted_date and extracted_password and extracted_confirmation_code:
        print("\nAll information extracted. Send verification request...")

        agent_verification_response = verify_answer(
            "mailbox",
            {
                "date": extracted_date,
                "password": extracted_password,
                "confirmation_code": extracted_confirmation_code,
            },
        )

        if agent_verification_response:
            print("Agent's response to verification instruction:")
            print(agent_verification_response)
        else:
            print("Agent did not respond to verification instruction.")

    print(
        f"\nFinal extracted info: Date={extracted_date}, Password={extracted_password}, Confirmation Code={extracted_confirmation_code}"
    )


if __name__ == "__main__":
    run_task9_mailbox("google/gemini-3-flash-preview")
