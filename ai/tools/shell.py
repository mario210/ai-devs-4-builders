from loguru import logger
import requests
import time
import urllib3
import os
from dotenv import load_dotenv

from ai.agent import AGENTS_API_KEY
from urllib3.exceptions import InsecureRequestWarning

# Load environment variables
load_dotenv()

# Disable warning globally
urllib3.disable_warnings(InsecureRequestWarning)


def _execute_api_request(url: str, payload: dict):
    """
    Internal helper function to send an API request and handle responses.
    Handles rate limiting and bans by waiting if necessary.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(0.5)  # Small timeout to prevent rapid API calls
            cmd = payload.get("answer", {}).get("cmd") or payload.get("cmd")
            logger.info(f"Executing shell command | url = {url} | cmd = [{cmd}]")
            response = requests.post(url, json=payload, verify=False)

            if response.status_code == 200:
                logger.info(
                    f"Command executed successfully. Response: {response.json()}"
                )
                return response.json()
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"error": response.text}

                if response.status_code in [429, 503]:
                    # Retry after wait
                    wait_time = 20
                    if "Retry-After" in response.headers:
                        try:
                            wait_time = int(response.headers["Retry-After"]) + 1
                        except ValueError:
                            pass
                    logger.warning(
                        f"Rate limited. Waiting {wait_time}s... {error_data}"
                    )
                    time.sleep(wait_time)
                    continue
                elif "ban" in str(error_data).lower():
                    wait_time = 20
                    if (
                        isinstance(error_data, dict)
                        and "ban" in error_data
                        and "ttl_seconds" in error_data["ban"]
                    ):
                        wait_time = int(error_data["ban"]["ttl_seconds"]) + 1
                    logger.warning(
                        f"Security ban applied. Waiting {wait_time}s to clear ban, then notifying agent..."
                    )
                    time.sleep(wait_time)
                    # Do NOT retry the same bad command. Return the error to the agent so it learns.
                    return {
                        "error": error_data,
                        "status_code": response.status_code,
                        "note": "Command rejected due to security policy. Do not retry this command.",
                    }
                elif isinstance(error_data, dict) and error_data.get("code") == -860:
                    logger.warning(f"Shell command output too large: {error_data}")
                    return {
                        "error": error_data,
                        "status_code": response.status_code,
                        "note": "Command output exceeded maximum size (4096 bytes). Try commands that limit output, such as `head`, `tail`, `grep` with more specific patterns, or piping output to `head -n X`.",
                    }
                else:
                    logger.error(f"Error from shell API: {error_data}")
                    return {"error": error_data, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Request failed: {e}")
            time.sleep(5)

    return {"error": "Failed after multiple retries"}


def run_shell_command(cmd: str):
    url = os.environ.get("HUB_API_SHELL_URL")
    payload = {"apikey": AGENTS_API_KEY, "answer": cmd}
    return _execute_api_request(url, payload)


def run_shell_command_v2(task_name: str, cmd: str):
    url = os.environ.get("HUB_API_VERIFY_URL")
    payload = {"apikey": AGENTS_API_KEY, "task": task_name, "answer": {"cmd": cmd}}
    return _execute_api_request(url, payload)
