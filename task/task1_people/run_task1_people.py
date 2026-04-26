import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
from loguru import logger
import argparse
import os
from enum import Enum
from typing import Dict, Any, Optional, List

import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ai.tools.hub_requests import verify_answer

# Load environment variables from .env file
load_dotenv()

# --- Constants ---
TARGET_YEAR = 2026
DEFAULT_DATA_PATH = "../../data/people.csv"

ALLOWED_TAGS = [
    "IT",
    "transport",
    "edukacja",
    "medycyna",
    "praca z ludźmi",
    "praca z pojazdami",
    "praca fizyczna",
]

# --- LangChain Pydantic Model for Structured Output ---
JobTagEnum = Enum("JobTagEnum", {tag: tag for tag in ALLOWED_TAGS})


class JobTags(BaseModel):
    """A model to hold the tags for a job profession."""

    tags: List[JobTagEnum] = Field(
        description=f"A list of tags relevant to the profession. You must use only tags from this list: {', '.join(ALLOWED_TAGS)}"
    )


def _process_row(row: pd.Series, chain: Any) -> Optional[Dict[str, Any]]:
    """
    Processes a single row from the DataFrame.

    It filters by gender, age, and city, then uses the AI agent to tag the job.
    Returns a dictionary with person data if all criteria are met, otherwise None.
    """
    try:
        # Basic filtering (gender, age, city) - these are now handled by DataFrame filtering
        # before calling this function, but keeping checks for robustness if called directly.
        if row["gender"].strip() != "M":
            return None

        birth_year = int(str(row["birthDate"]).strip().split("-")[0])
        age = TARGET_YEAR - birth_year
        if not (20 <= age <= 40):
            return None

        if "Grudziądz" not in row["birthPlace"].strip():
            return None

        # Use AI for job tagging
        job_title = row["job"].strip()
        if not job_title:
            return None

        # Invoke the LangChain chain to get structured output
        content = chain.invoke({"job_title": job_title})

        if not content:
            logger.warning(f"No content returned from LLM for job: {job_title}")
            return None

        # Convert enum members to their string values for processing
        tags = [tag.value for tag in content.tags]

        if "transport" in tags:
            return {
                "name": row["name"].strip(),
                "surname": row["surname"].strip(),
                "gender": "M",
                "born": birth_year,
                "city": row["birthPlace"].strip(),
                "tags": tags,
            }

    except (ValueError, IndexError, KeyError) as e:
        logger.warning(
            f"Skipping row due to processing error: {e}. Row: {row.to_dict()}"
        )

    return None


def run_task1_people(file_path: str, agent_model: str) -> None:
    """
    Runs the 'People' task.

    This task involves:
    1. Reading a CSV file of people's data using pandas.
    2. Filtering records based on specific criteria (gender, age, city) using pandas.
    3. Using an AI agent to tag the profession for filtered records.
    4. Collecting records tagged with 'transport'.
    5. Verifying the final list of people with an external service.

    Args:
        file_path: Path to the CSV data file.
        agent_model: The identifier for the AI model to use.
    """
    logger.info("--- Running Task 1: People (CSV Filtering & Job Tagging) ---")

    # --- LangChain Setup ---
    # Extract model name from the provided string (e.g., 'openai/gpt-4o-mini' -> 'gpt-4o-mini')
    model_name = agent_model.split("/")[-1]
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )
    structured_llm = llm.with_structured_output(JobTags)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"You are an HR assistant. Assign tags to a profession based on its title. "
                f"You must use only tags from the following list: {', '.join(ALLOWED_TAGS)}",
            ),
            ("user", "Profession: {job_title}"),
        ]
    )

    chain = prompt | structured_llm
    # --- End LangChain Setup ---

    results = []
    try:
        # Read CSV using pandas
        df = pd.read_csv(file_path)

        # Apply initial filters using pandas DataFrame operations
        df_filtered = df[
            (df["gender"].str.strip() == "M")
            & (df["birthPlace"].str.contains("Grudziądz", na=False))
        ].copy()  # Use .copy() to avoid SettingWithCopyWarning

        # Calculate age and apply age filter
        df_filtered["birth_year"] = (
            df_filtered["birthDate"].str.split("-").str[0].astype(int)
        )
        df_filtered["age"] = TARGET_YEAR - df_filtered["birth_year"]
        df_filtered = df_filtered[
            (df_filtered["age"] >= 20) & (df_filtered["age"] <= 40)
        ]

        # Iterate through the filtered DataFrame rows and process with AI
        for index, row in df_filtered.iterrows():
            person_data = _process_row(row, chain)
            if person_data:
                results.append(person_data)

    except FileNotFoundError:
        logger.error(f"The file at {file_path} was not found.", exc_info=True)
        return
    except pd.errors.EmptyDataError:
        logger.error(f"The file at {file_path} is empty.", exc_info=True)
        return
    except KeyError as e:
        logger.error(f"Missing expected column in CSV: {e}", exc_info=True)
        return
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return

    logger.info(f"Found {len(results)} matching records.")
    final_answer = json.dumps(results, indent=2, ensure_ascii=False)
    logger.info(f"Final Answer Payload:\n{final_answer}")

    verify_answer("people", final_answer)


def main() -> None:
    """Main function to run the task from the command line."""
    parser = argparse.ArgumentParser(description="Run the People task.")
    parser.add_argument(
        "--file_path",
        type=str,
        default=DEFAULT_DATA_PATH,
        help="Path to the people.csv data file.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-4o-mini",
        help="The AI model to use for the agent.",
    )
    args = parser.parse_args()

    run_task1_people(file_path=args.file_path, agent_model=args.model)


if __name__ == "__main__":
    main()
