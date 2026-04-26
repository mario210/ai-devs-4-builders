import os
from datetime import datetime


def parse_log_line(line):
    """
    Parses a log line to extract timestamp, level, and the full message.
    Example: [2026-03-17 06:00:16] [INFO] Primary feed acknowledgment...
    Returns a tuple (datetime_obj, level, original_line, description).
    """
    try:
        parts = line.strip().split("] [")
        timestamp_str = parts[0][1:]
        level_part = parts[1].split("] ")

        dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        level = level_part[0]
        description = level_part[1] if len(level_part) > 1 else ""

        return dt_obj, level, line.strip(), description
    except (ValueError, IndexError):
        return None, None, None, None


def filter_logs(log_path: str = "data/failure.log", **kwargs) -> str:
    """
    Reads a log file and filters it to include the last 11 unique entries for each
    of the 'INFO', 'WARN', 'ERRO', and 'CRIT' severity levels. Uniqueness is based on the
    log message content (description), ignoring the timestamp. The final output is sorted chronologically.
    """
    if not os.path.exists(log_path):
        return "Log file not found."

    levels_to_keep = ["INFO", "WARN", "ERRO", "CRIT"]
    log_entries = {level: [] for level in levels_to_keep}

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            dt_obj, level, original_line, description = parse_log_line(line)
            if dt_obj and level in levels_to_keep:
                log_entries[level].append((dt_obj, original_line, description))

    final_logs = []
    for level in levels_to_keep:
        # Sort by timestamp (most recent first)
        sorted_by_time = sorted(log_entries[level], key=lambda x: x[0], reverse=True)

        unique_logs_for_level = []
        seen_descriptions = set()

        for dt_obj, original_line, description in sorted_by_time:
            if description not in seen_descriptions:
                seen_descriptions.add(description)
                unique_logs_for_level.append((dt_obj, original_line))

            # Stop when we have 11 unique logs for this level
            if len(unique_logs_for_level) >= 15:
                break

        final_logs.extend(unique_logs_for_level)

    # Sort the combined list of unique logs chronologically
    final_logs_sorted = sorted(final_logs, key=lambda x: x[0])

    return "\n".join([log[1] for log in final_logs_sorted])


TASK8_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "filter_logs",
            "description": "Reads a log file and filters it to include the last 11 unique entries for each of 'INFO', 'WARN', 'ERRO', and 'CRIT' levels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "log_path": {
                        "type": "string",
                        "description": "Path to the log file. Defaults to data/failure.log",
                    }
                },
                "required": [],
            },
        },
    }
]

TASK8_TOOL_MAP = {
    "filter_logs": filter_logs,
}
