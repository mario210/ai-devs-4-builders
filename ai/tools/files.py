import requests
import os


def read_csv_from_url(url: str) -> str:
    """Fetches a CSV file from a given URL and returns its content."""
    try:
        print(f"Fetching from {url}...")
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        return f"Error fetching CSV from {url}: {e}"


def read_file_content(file_path: str) -> str:
    """Reads a file from a local path and returns its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file {file_path}: {e}"


def download_file(file_url: str, save_path: str = "file.log") -> str:
    """
    Downloads a file from a specified URL if it doesn't already exist.
    """
    if os.path.exists(save_path):
        return f"File already exists at {save_path}"

    try:
        response = requests.get(file_url)
        response.raise_for_status()
        # Ensure the directory for save_path exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return f"File downloaded and saved to {save_path}"
    except requests.RequestException as e:
        return f"Error downloading file: {e}"
