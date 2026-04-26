import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
from dotenv import load_dotenv
from loguru import logger
from ai.agent import AGENTS_API_KEY
from ai.tools.hub_requests import post_json_request

# Load environment variables
load_dotenv()

ZMAIL_API_URL = os.environ.get("HUB_API_ZMAIL_URL")


def _mailbox_action_request(
    action, page=None, mail_id=None, query=None
):  # Modified to accept query
    logger.info(
        f"  -> Calling {ZMAIL_API_URL} to perform action '{action}' on mailbox."
    )

    payload = {
        "apikey": AGENTS_API_KEY,
        "action": action,
    }
    if page is not None:
        payload["page"] = page
    if mail_id is not None:
        # Note: action getMessages expects 'ids' not 'id' based on help response,
        # but let's stick to whatever worked previously if it did, or fix it based on the new help response.
        # Help response: "action": "getMessages", "ids": "Required..."
        if action == "getMessages":
            payload["ids"] = mail_id
        else:
            payload["id"] = mail_id
    if query is not None:
        payload["query"] = query

    return post_json_request(payload, ZMAIL_API_URL)


def mail_check_available_actions():
    """
    Checks available actions for the mailbox.
    """
    return _mailbox_action_request(action="help")


def mail_get_inbox(page):
    """
    Retrieves the inbox content for a given page.
    """
    return _mailbox_action_request(action="getInbox", page=page)


def mail_get_content_by_id(mail_id):
    """
    Retrieves the full content of a specific email by its ID.
    """
    # Changed action to getMessages based on help response
    return _mailbox_action_request(action="getMessages", mail_id=mail_id)


def mail_search(query, page=1):
    """
    Searches mailbox.
    """
    return _mailbox_action_request(action="search", query=query, page=page)


MAILBOX_REQUESTS_TOOLS = {
    "mail_check_available_actions": {
        "name": "mail_check_available_actions",
        "description": "Checks available actions for the mailbox.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "mail_get_inbox": {
        "name": "mail_get_inbox",
        "description": "Retrieves the content of the inbox for a given page.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "The page number for the inbox content.",
                }
            },
            "required": ["page"],
        },
    },
    "mail_get_content_by_id": {
        "name": "mail_get_content_by_id",
        "description": "Retrieves the full content of a specific email by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "mail_id": {
                    "type": "string",
                    "description": "The ID of the email to retrieve.",
                }
            },
            "required": ["mail_id"],
        },
    },
    "mail_search": {
        "name": "mail_search",
        "description": "Searches messages with full-text style query and Gmail-like operators (e.g., from:, to:, subject:).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "page": {
                    "type": "integer",
                    "description": "The page number. Default: 1.",
                },
            },
            "required": ["query"],
        },
    },
}

MAILBOX_REQUESTS_TOOLS_MAP = {
    "mail_check_available_actions": mail_check_available_actions,
    "mail_get_inbox": mail_get_inbox,
    "mail_get_content_by_id": mail_get_content_by_id,
    "mail_search": mail_search,
}
