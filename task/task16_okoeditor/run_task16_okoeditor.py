import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
import argparse
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from ai.agent import Agent, AGENTS_API_KEY
from ai.memory import SharedMemory
from ai.tools.hub_requests import verify_answer

# Load environment variables from .env file
load_dotenv()

# --- Constants ---
AGENT_MODEL = "google/gemini-3.1-pro-preview"
TASK_NAME = "okoeditor"
OKO_URL = os.environ.get("HUB_OKO_URL")
OKO_USER = os.environ.get("HUB_OKO_USER")
OKO_PASS = os.environ.get("HUB_OKO_PASS")

# --- Shared Memory ---
memory = SharedMemory()


def help_action():
    """Prints the help message for the Okoeditor API."""
    return verify_answer(TASK_NAME, {"action": "help"})


def update_action(
    page: str, id: str, content: str = None, title: str = None, done: str = None
):
    """Updates an item in the Okoeditor."""
    logger.info(
        f"Calling update_action: page={page}, id={id}, title={title}, content={content}, done={done}"
    )
    answer = {
        "action": "update",
        "page": page,
        "id": id,
    }
    if content:
        answer["content"] = content
    if title:
        answer["title"] = title
    if done:
        answer["done"] = done
    return verify_answer(TASK_NAME, answer)


def done_action():
    """Verifies if all required data edits are completed."""
    logger.info("Calling done_action.")
    return verify_answer(TASK_NAME, {"action": "done"})


def login_and_scrape_page(
    login: str, password: str, access_key: str, target_url: str
) -> str:
    """
    Performs a login using Playwright, scrapes the main page and all subpages,
    and stores the content in shared memory.
    """
    logger.info(
        f"Attempting to login with user: {login} and scrape {target_url} using Playwright"
    )

    all_scraped_content = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        try:
            logger.info(f"Navigating to {OKO_URL}")
            page.goto(OKO_URL)
            page.wait_for_selector('input[name="login"]')
            page.fill('input[name="login"]', login)
            page.fill('input[name="password"]', password)
            page.fill('input[name="access_key"]', access_key)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            start_url = page.url
            logger.info(f"Successfully logged in. Current URL: {start_url}")

            urls_to_visit = {start_url}
            visited_urls = set()

            while urls_to_visit:
                current_url = urls_to_visit.pop()
                normalized_url = urlparse(current_url)._replace(fragment="").geturl()

                if (
                    normalized_url in visited_urls
                    or urlparse(normalized_url).netloc != urlparse(OKO_URL).netloc
                    or "/delete" in normalized_url
                    or "/edit" in normalized_url
                    or "/uzytkownicy" in normalized_url
                    or "/notatki" in normalized_url
                ):
                    continue

                try:
                    logger.info(f"Crawling page: {normalized_url}")
                    page.goto(normalized_url)
                    page.wait_for_load_state("networkidle")
                    content = page.content()

                    all_scraped_content[normalized_url] = content
                    visited_urls.add(normalized_url)

                    soup = BeautifulSoup(content, "html.parser")
                    for link in soup.find_all("a", href=True):
                        full_url = urljoin(normalized_url, link["href"])
                        normalized_link_url = (
                            urlparse(full_url)._replace(fragment="").geturl()
                        )
                        if (
                            normalized_link_url not in visited_urls
                            and "/delete" not in normalized_link_url
                            and "/edit" not in normalized_link_url
                            and "/uzytkownicy" not in normalized_link_url
                            and "/notatki" not in normalized_link_url
                        ):
                            urls_to_visit.add(full_url)
                except Exception as e:
                    logger.warning(f"Could not crawl page {normalized_url}: {e}")

            memory.set("scraped_content", all_scraped_content)
            return "Successfully logged in and scraped data has been stored in memory."
        finally:
            browser.close()


def run_task16_okoeditor(agent_model: str) -> None:
    logger.info("--- Running Task 16: Okoeditor ---")

    agent = Agent(default_model=agent_model)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "login_and_scrape_page",
                "description": "Logs into the Okoeditor website, scrapes its content and all subpages, and stores them in memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "login": {"type": "string"},
                        "password": {"type": "string"},
                        "access_key": {"type": "string"},
                        "target_url": {"type": "string"},
                    },
                    "required": ["login", "password", "access_key", "target_url"],
                },
            },
        }
    ]
    tool_map = {"login_and_scrape_page": login_and_scrape_page}

    # --- Step 1: Login and Scrape Data ---
    login_messages = [
        {
            "role": "user",
            "content": f"Please log into {OKO_URL} with user '{OKO_USER}', pass '{OKO_PASS}', and key '{AGENTS_API_KEY}'. The target_url is {OKO_URL}. Scrape the page you land on and all accessible subpages except that which has in the url: /delete or /edit. ",
        }
    ]
    agent.chat(messages=login_messages, tools=tools, tool_map=tool_map)

    # --- Step 2: Analyze Scraped Data and Perform Updates ---
    scraped_data = memory.get("scraped_content")
    if not scraped_data:
        logger.error("Could not retrieve scraped data from memory. Aborting.")
        return

    skolwin_incident_id = None
    skolwin_task_id = None
    komarowo_incident_id = None
    id_pattern = re.compile(r"[0-9a-fA-F]{32}")

    all_incident_ids_and_content = (
        {}
    )  # To store all incident IDs and their text content for Komarowo selection

    for url, html_content in scraped_data.items():
        parsed_url = urlparse(url)
        path_segments = parsed_url.path.split("/")

        current_id_from_url = None
        if len(path_segments) > 2 and id_pattern.fullmatch(path_segments[-1]):
            current_id_from_url = path_segments[-1]

        soup = BeautifulSoup(html_content, "html.parser")
        page_text = soup.get_text()  # Get all visible text on the page

        if "incydenty" in url:
            if current_id_from_url:
                all_incident_ids_and_content[current_id_from_url] = page_text

            if "Skolwin" in page_text and not skolwin_incident_id:
                skolwin_incident_id = current_id_from_url

        elif "zadania" in url:
            if "Skolwin" in page_text and not skolwin_task_id:
                skolwin_task_id = current_id_from_url

    # Now, determine komarowo_incident_id from the collected incident data
    if skolwin_incident_id:  # Ensure we have Skolwin's ID to avoid reusing it
        for incident_id, content in all_incident_ids_and_content.items():
            if incident_id == skolwin_incident_id:
                continue  # Skip Skolwin's own incident

            # Check if the content does not mention Skolwin or Komarowo
            # if "Domatowo" in content:
            if "Skolwin" not in content and "Komarowo" not in content:
                komarowo_incident_id = incident_id
                break  # Found a suitable incident for Komarowo

    if not all([skolwin_incident_id, skolwin_task_id, komarowo_incident_id]):
        logger.error("Failed to find all necessary IDs from scraped data.")
        # Log more details for debugging
        logger.error(f"Skolwin Incident ID found: {skolwin_incident_id}")
        logger.error(f"Skolwin Task ID found: {skolwin_task_id}")
        logger.error(f"Komarowo Reuse Incident ID found: {komarowo_incident_id}")
        logger.error(f"All scraped URLs: {list(scraped_data.keys())}")
        return

    logger.info(
        f"Final IDs: Skolwin Incident={skolwin_incident_id}, Skolwin Task={skolwin_task_id}, Komarowo Reuse Incident={komarowo_incident_id}"
    )

    # --- Step 3: Perform Updates ---
    response = update_action(
        "incydenty",
        skolwin_incident_id,
        title="MOVE04 Aktywność bobrów w Skolwinie",
        content="W rejonie Skolwina zaobserwowano wzmożoną aktywność bobrów, budujących tamy i zmieniających krajobraz wodny. Wymaga to pilnej uwagi.",
    )
    if response and response.get("code") == -775:
        logger.error(f"API Error: {response.get('message')}. Aborting.")
        return

    response = update_action(
        "zadania",
        skolwin_task_id,
        content="W mieście Skolwin widziano bobry.",
        done="YES",
    )
    if response and response.get("code") == -775:
        logger.error(f"API Error: {response.get('message')}. Aborting.")
        return

    response = update_action(
        "incydenty",
        komarowo_incident_id,
        title="MOVE01 Wykryto ruch ludzi w okolicach miasta Komarowo",
        content="System nasłuchu komunikacji internetowej wykrył wzmożoną aktywność sieciową oraz nietypowe wzorce komunikacji wskazujące na obecność ludzi w opuszczonym mieście Komarowo. Analiza danych sugeruje koordynowany ruch grup. Wymagana jest natychmiastowa weryfikacja terenowa.",
    )
    if response and response.get("code") == -775:
        logger.error(f"API Error: {response.get('message')}. Aborting.")
        return

    # --- Step 4: Finalize ---
    done_action()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Task 16.")
    parser.add_argument("--model", type=str, default=AGENT_MODEL)
    args = parser.parse_args()
    run_task16_okoeditor(agent_model=args.model)


if __name__ == "__main__":
    # help_action()
    main()
