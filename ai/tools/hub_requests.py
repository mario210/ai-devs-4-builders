import json
import time
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

import httpx
import copy
from loguru import logger
from ai.agent import AGENTS_API_KEY

# Load environment variables
load_dotenv()

VERIFY_API_URL = os.environ.get("HUB_API_VERIFY_URL")

# Create a single, reusable client instance for performance (connection pooling).
# WARNING: Disabling SSL verification (`verify=False`) is insecure and should
# be avoided in production. It's present to mimic original behavior but it is
# strongly recommended to remove it and handle SSL correctly.
_client = httpx.Client(verify=False, timeout=30.0)


def post_json_request(payload, url):
    """
    Sends a JSON POST request to the specified URL with the given payload.
    Handles rate limiting by checking 'Retry-After' header.
    """
    # Avoid logging sensitive data like API keys by creating a redacted copy for logging.
    log_payload = copy.deepcopy(payload)
    if "apikey" in log_payload:
        log_payload["apikey"] = "[REDACTED]"

    try:
        # logger.info(f"  -> Calling external API: {url} with payload: {log_payload}")
        response = _client.post(url, json=payload)

        # Check headers for rate limits
        if "Retry-After" in response.headers:
            try:
                wait_time = int(response.headers["Retry-After"])
                logger.warning(
                    f"  !! Rate limit hit (Retry-After). Waiting {wait_time} seconds..."
                )
                time.sleep(wait_time + 1)
            except (ValueError, TypeError):
                logger.warning(
                    f"  !! Rate limit hit, but couldn't parse 'Retry-After' header: {response.headers.get('Retry-After')}"
                )

        response.raise_for_status()

        resp_data = response.json()
        # logger.info(f"  <- External API response: {resp_data}")
        return resp_data

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP Status Error occurred for request: {e.request.method} {e.request.url}"
        )
        logger.error(f"Response Status Code: {e.response.status_code}")
        logger.error(f"Response Headers: {e.response.headers}")
        logger.error(f"Response Content: {e.response.text}")
        # return {"error": f"API call failed with status {e.response.status_code}: {e.response.text}"}
        return json.loads(e.response.text)
    except httpx.RequestError as e:
        logger.error(f"An unexpected request error occurred: {e}")
        if hasattr(e, "response") and e.response is not None:
            error_message = e.response.text
            logger.error(f"Response content: {error_message}")
        # Handle cases where there is no response (e.g., network error)
        return {"error": str(e)}


def verify_answer(task_name, answer_payload):
    payload = {"apikey": AGENTS_API_KEY, "task": task_name, "answer": answer_payload}
    response = post_json_request(payload, VERIFY_API_URL)
    _handle_verification(response)
    return response


def retry_verify_answer(task_name, answer_payload, retries=10, delay_seconds=5):
    """
    Retries the verify_answer call with a fixed delay between attempts.
    """
    for attempt in range(retries):
        try:
            result = verify_answer(task_name, answer_payload)
            if result is not None:
                return result
            logger.warning(
                f"Attempt {attempt+1}: verify_answer returned None (indicating failure). Retrying..."
            )
        except Exception as e:
            logger.error(
                f"Attempt {attempt+1}: Exception during verify_answer: {e}. Retrying..."
            )
        time.sleep(delay_seconds)
    logger.error(f"Failed to verify answer after {retries} attempts.")
    return None


def _handle_verification(verification_result: Optional[Dict[str, Any]]) -> None:
    """Handles the verification result by logging the outcome."""
    if verification_result and verification_result.get("code") == 0:
        logger.info("--- Verification SUCCESSFUL! ---")
        logger.info(f"Flag captured: {verification_result.get('message')}")
