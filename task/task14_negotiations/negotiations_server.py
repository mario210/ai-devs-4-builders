import http.server
import socketserver
import json
import csv
from io import StringIO
import os
from ai.tools.files import read_file_content
from typing import Set

# This will store the data in the format: { "city_name": {"item1", "item2"}, ... }
city_items_data: dict[str, Set[str]] = {}
item_code_to_name: dict[str, str] = {}
city_code_to_name: dict[str, str] = {}

# Base directory for data files
DATA_DIR = "../../data/negotiations_data/"


def load_data_from_csvs():
    global city_items_data, item_code_to_name, city_code_to_name

    # 1. Load items.csv
    items_filepath = os.path.join(DATA_DIR, "items.csv")
    items_csv_content = read_file_content(items_filepath)
    if "Error" in items_csv_content:
        print(f"Error loading items.csv: {items_csv_content}")
        return

    reader = csv.reader(StringIO(items_csv_content))
    next(reader)  # Skip header
    for row in reader:
        if len(row) == 2:
            name, code = row
            item_code_to_name[code] = name
    print(f"Loaded {len(item_code_to_name)} items.")

    # 2. Load cities.csv
    cities_filepath = os.path.join(DATA_DIR, "cities.csv")
    cities_csv_content = read_file_content(cities_filepath)
    if "Error" in cities_csv_content:
        print(f"Error loading cities.csv: {cities_csv_content}")
        return

    reader = csv.reader(StringIO(cities_csv_content))
    next(reader)  # Skip header
    for row in reader:
        if len(row) == 2:
            name, code = row
            city_code_to_name[code] = name
    print(f"Loaded {len(city_code_to_name)} cities.")

    # 3. Load connections.csv
    connections_filepath = os.path.join(DATA_DIR, "connections.csv")
    connections_csv_content = read_file_content(connections_filepath)
    if "Error" in connections_csv_content:
        print(f"Error loading connections.csv: {connections_csv_content}")
        return

    reader = csv.reader(StringIO(connections_csv_content))
    next(reader)  # Skip header
    for row in reader:
        if len(row) == 2:
            item_code, city_code = row
            item_name = item_code_to_name.get(item_code)
            city_name = city_code_to_name.get(city_code)

            if item_name and city_name:
                city_items_data.setdefault(city_name, set()).add(item_name)
    print(f"Populated data for {len(city_items_data)} cities with items.")


# Helper function to find the best matching canonical item name
def _find_best_matching_canonical_item(query_item_name: str) -> Optional[str]:
    """
    Attempts to find the best matching canonical item name from the loaded items
    based on the query string. It uses a word-based matching strategy.
    """
    # Normalize query: lowercase, remove common filler words, split into words
    normalized_query_words = set(
        query_item_name.lower()
        .replace("mająca", "")
        .replace("moc", "")
        .replace("i", "")
        .replace("długości", "")
        .replace("metrów", "")
        .split()
    )

    if not normalized_query_words:
        return None

    best_match = None
    max_matching_words = 0

    for canonical_name in item_code_to_name.values():
        normalized_canonical_words = set(canonical_name.lower().split())

        matching_words_count = len(
            normalized_query_words.intersection(normalized_canonical_words)
        )

        # Prioritize matches where all query words are present in the canonical name
        if normalized_query_words.issubset(normalized_canonical_words):
            if (
                best_match is None
                or matching_words_count > max_matching_words
                or (
                    matching_words_count == max_matching_words
                    and len(canonical_name) < len(best_match)
                )
            ):
                best_match = canonical_name
                max_matching_words = matching_words_count
        elif matching_words_count > max_matching_words:
            best_match = canonical_name
            max_matching_words = matching_words_count
        elif matching_words_count == max_matching_words and best_match is not None:
            if len(canonical_name) < len(best_match):
                best_match = canonical_name

    return best_match


# Modified function that expects a canonical item name
def handle_find_cities_for_item(item_name: str):
    """
    Finds cities that offer a specific item.
    Expects a canonical item name.
    """
    print(f"handle_find_cities_for_item - Input: item_name='{item_name}'")
    if not item_name:
        print("handle_find_cities_for_item - Output: No item name provided (400)")
        return {"output": "No item name provided for search."}, 400

    # Attempt to find the best matching canonical item name
    resolved_item_name = _find_best_matching_canonical_item(item_name)

    if not resolved_item_name:
        print(
            f"handle_find_cities_for_item - Output: Could not resolve item '{item_name}' (400)"
        )
        return {
            "output": f"Could not resolve item: '{item_name}'. Please provide a more precise description."
        }, 400

    if (
        resolved_item_name not in item_code_to_name.values()
    ):  # Should not happen if _find_best_matching_canonical_item works
        print(
            f"handle_find_cities_for_item - Output: Resolved item '{resolved_item_name}' not found in database (400)"
        )
        # You can return 404 or 400, depending on API policy
        return {
            "output": f"Internal error: Resolved item '{resolved_item_name}' not found."
        }, 400

    found_cities = []
    for city, items in city_items_data.items():
        if resolved_item_name in items:
            found_cities.append(city)

    if found_cities:
        output_message = ", ".join(sorted(found_cities))  # Sorting for consistency
    else:
        output_message = f"No cities found offering {resolved_item_name}."

    # Ensure output does not exceed 500 bytes and is not shorter than 4 bytes
    output_message_bytes = output_message.encode("utf-8")
    if len(output_message_bytes) > 500:
        output_message = output_message_bytes[:497].decode("utf-8", "ignore") + "..."
    elif len(output_message_bytes) < 4:
        output_message = "..."  # Or some other minimal message

    print(f"handle_find_cities_for_item - Output: '{output_message}' (200)")
    return {"output": output_message, "resolved_item": resolved_item_name}, 200


class JSONRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            params = data.get("params")

            response_data = {}
            status_code = 200

            if self.path == "/find_cities_for_item":
                # Expects params to be a string (canonical item name)
                if not isinstance(params, str):
                    response_data = {
                        "output": "Error: 'params' must be a string for /find_cities_for_item."
                    }
                    status_code = 400
                else:
                    response_data, status_code = handle_find_cities_for_item(params)
            else:
                response_data = {"output": "Error: Unknown endpoint"}
                status_code = 404

        except json.JSONDecodeError:
            response_data = {"output": "Error: Invalid JSON"}
        except Exception as e:
            response_data = {"output": f"Error: {str(e)}"}
            status_code = 500

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))


def run_server(port: int):
    load_data_from_csvs()  # Load data when the server starts
    # Allow reuse of address to avoid "Address already in use" errors during quick restarts
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), JSONRequestHandler) as httpd:
        print(f"Negotiations server started at port {port}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    run_server(3000)
