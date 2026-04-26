from ai.tools.hub_requests import post_json_request, verify_answer, retry_verify_answer
from ai.tools.files import read_csv_from_url, read_file_content, download_file
from ai.tools.document_crawler import fetch_doc_and_links
from ai.tools.image import analyze_image
from ai.tools.shell import run_shell_command, run_shell_command_v2

HUB_REQUESTS_TOOLS = {
    "post_json_request": {
        "name": "post_json_request",
        "description": "Sends a JSON POST request to the specified URL with the given payload. Handles rate limiting by checking 'Retry-After' header.",
        "parameters": {
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "description": "The JSON payload to send in the request body."
                },
                "url": {
                    "type": "string",
                    "description": "The URL to send the POST request to."
                }
            },
            "required": ["payload", "url"]
        }
    },
    "send_verification_request": {
        "name": "send_verification_request",
        "description": "Sends a verification request with a task and an answer to the verification API.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task identifier for verification."
                },
                "answer": {
                    "type": "string",
                    "description": "The answer to be verified."
                }
            },
            "required": ["task", "answer"]
        }
    },
    "retry_send_verification_request": {
        "name": "retry_send_verification_request",
        "description": "Sends a verification request with a task and an answer to the verification API and retries if request fails.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task identifier for verification."
                },
                "answer": {
                    "type": "string",
                    "description": "The answer to be verified."
                },
                "retries": {
                    "type": "integer",
                    "description": "Optional. Number of times to retry the verification. Default is 10."
                },
                "delay_seconds": {
                    "type": "integer",
                    "description": "Optional. Delay in seconds between retry attempts. Default is 5."
                },
            },
            "required": ["task", "answer"]
        }
    },
    "mail_check_available_actions": {
        "name": "mail_check_available_actions",
        "description": "Checks available actions for the mailbox.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "mail_get_inbox": {
        "name": "mail_get_inbox",
        "description": "Retrieves the content of the inbox for a given page.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "The page number for the inbox content."
                }
            },
            "required": ["page"]
        }
    },
    "mail_get_content_by_id": {
        "name": "mail_get_content_by_id",
        "description": "Retrieves the full content of a specific email by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "mail_id": {
                    "type": "string",
                    "description": "The ID of the email to retrieve."
                }
            },
            "required": ["mail_id"]
        }
    },
    "mail_search": {
        "name": "mail_search",
        "description": "Searches messages with full-text style query and Gmail-like operators (e.g., from:, to:, subject:).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query."
                },
                "page": {
                    "type": "integer",
                    "description": "The page number. Default: 1."
                }
            },
            "required": ["query"]
        }
    }
}

FILES_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_csv_from_url",
            "description": "Fetches a CSV file from a provided URL and returns its raw text content. This tool is for remote CSV files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL endpoint to fetch the CSV file from."
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Reads the content of a local file from a specified path and returns its raw text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the local CSV file."
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "download_file",
            "description": "Downloads a file from a specified URL if it doesn't already exist. File should be saved in /data directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_url": {
                        "type": "string",
                        "description": "The URL of the file to download."
                    },
                    "save_path": {
                        "type": "string",
                        "description": "The local path to save the file. By default, files are saved in the 'data/' directory.",
                        "default": "data/downloaded_file.log"
                    }
                },
                "required": ["file_url"],
            },
        },
    }
]

# Define tools for document crawling and analysis
DOCUMENT_CRAWLER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_doc_and_links",
            "description": "Pobiera główny dokument i wszystkie linkowane w nim zasoby (tekstowe i obrazkowe), a następnie analizuje je. Zwraca pełną treść zebraną z linków.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Pełny adres URL dokumentu, z którego mają być pobrane dane i linki (musi zawierać nazwę pliku)."
                    }
                },
                "required": ["url"],
            },
        },
    },
]

IMAGES_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Reads a local image file and uses an LLM to describe its content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The path to the image file to describe."
                    },
                    "agent_model": {
                        "type": "string",
                        "description": "Optional. The model to use for the analysis (e.g., 'openai/gpt-5.4', 'google/gemini-pro-vision')."
                    }
                },
                "required": ["filename"]
            }
        }
    }
]

SHELL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Execute a shell command on the remote restricted virtual machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "The shell command to execute."
                    }
                },
                "required": ["cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell_command_v2",
            "description": "Execute a shell command on the remote restricted virtual machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_name": {
                        "type": "string",
                        "description": "The task identifier."
                    },
                    "cmd": {
                        "type": "string",
                        "description": "The shell command to execute."
                    }
                },
                "required": ["task_name", "cmd"]
            }
        }
    }
]

# Combine all tools into a single list for easier ai integration
ALL_AGENT_TOOlS = list(
    HUB_REQUESTS_TOOLS.values()) + FILES_TOOLS + DOCUMENT_CRAWLER_TOOLS + IMAGES_TOOLS + SHELL_TOOLS

# Create a single tool map for all functions
ALL_TOOL_MAP = {
    "post_json_request": post_json_request,
    "send_verification_request": verify_answer,
    "retry_send_verification_request": retry_verify_answer,
    "read_file_content": read_file_content,
    "read_csv_from_url": read_csv_from_url,
    "download_file": download_file,
    "fetch_doc_and_links": fetch_doc_and_links,
    "analyze_image": analyze_image,
    "run_shell_command": run_shell_command,
}

HUB_REQUESTS_TOOLS_MAP = {
    "post_json_request": post_json_request,
    "send_verification_request": verify_answer,
    "retry_send_verification_request": retry_verify_answer,
}

DOCUMENT_CRAWLER_TOOLS_MAP = {
    "fetch_doc_and_links": fetch_doc_and_links
}

FILES_TOOLS_MAP = {
    "read_file_content": read_file_content,
    "read_csv_from_url": read_csv_from_url,
    "download_file": download_file,
}

IMAGE_TOOLS_MAP = {
    "analyze_image": analyze_image
}

SHELL_TOOLS_MAP = {
    "run_shell_command": run_shell_command,
    "run_shell_command_v2": run_shell_command_v2
}
