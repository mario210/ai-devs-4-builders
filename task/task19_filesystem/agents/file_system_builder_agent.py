import json
import unicodedata
from ai.task import BaseTask
from ai.tools.hub_requests import verify_answer


def normalize_name(name):
    """
    Removes Polish diacritics, replaces spaces with underscores, and converts to lowercase.
    Example: 'Łódź' -> 'lodz', 'Jan Kowalski' -> 'jan_kowalski'
    """
    nfkd_form = unicodedata.normalize("NFKD", name)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    only_ascii = only_ascii.replace("ł", "l").replace("Ł", "L")
    return only_ascii.replace(" ", "_").lower()


class FileSystemBuilderAgent(BaseTask):
    def __init__(self, agent_model, memory):
        super().__init__("FileSystemBuilderAgent", agent_model, memory)

    def execute(self):
        print("FileSystemBuilderAgent: Starting execution...")

        task_name = self.memory.get("task_name")
        structured_notes_str = self.memory.get("structured_notes")

        if not structured_notes_str:
            print("Error: Structured notes not found in memory.")
            return

        try:
            notes = json.loads(structured_notes_str)
        except json.JSONDecodeError:
            print("Error: Failed to decode structured notes from memory.")
            return

        batch_actions = []

        # First, create the necessary directories
        batch_actions.append({"action": "createDirectory", "path": "/miasta"})
        batch_actions.append({"action": "createDirectory", "path": "/osoby"})
        batch_actions.append({"action": "createDirectory", "path": "/towary"})
        print("Added directory creation actions.")

        # 1. Create /miasta files
        for city, goods in notes.get("goods_bought", {}).items():
            city_normalized = normalize_name(city)
            content_data = {normalize_name(k): v for k, v in goods.items() if v > 0}
            file_content = json.dumps(content_data)
            file_path = f"/miasta/{city_normalized}"
            print(f"  /miasta: Path='{file_path}', Content='{file_content}'")
            batch_actions.append(
                {"action": "createFile", "path": file_path, "content": file_content}
            )

        # 2. Create /osoby files
        for city, manager in notes.get("trade_managers", {}).items():
            manager_normalized = normalize_name(manager)
            city_normalized = normalize_name(city)
            file_content = f"[{city_normalized}](/miasta/{city_normalized})"
            file_path = f"/osoby/{manager_normalized}"
            print(f"  /osoby: Path='{file_path}', Content='{file_content}'")
            batch_actions.append(
                {"action": "createFile", "path": file_path, "content": file_content}
            )

        # 3. Create /towary files (handling multiple sellers for one item)
        goods_to_cities = {}
        for city, goods in notes.get("goods_sold", {}).items():
            city_normalized = normalize_name(city)
            for good in goods.keys():
                good_normalized = normalize_name(good)
                if good_normalized not in goods_to_cities:
                    goods_to_cities[good_normalized] = []
                if city_normalized not in goods_to_cities[good_normalized]:
                    goods_to_cities[good_normalized].append(city_normalized)

        for good, cities in goods_to_cities.items():
            if cities:
                links = [f"[{city}](/miasta/{city})" for city in cities]
                file_content = "\n".join(links)
                file_path = f"/towary/{good}"
                print(f"  /towary: Path='{file_path}', Content='{file_content}'")
                batch_actions.append(
                    {"action": "createFile", "path": file_path, "content": file_content}
                )

        if batch_actions:
            print(
                f"Sending {len(batch_actions)} batch actions to create the filesystem."
            )
            verify_answer(task_name, batch_actions)
        else:
            print("No actions generated. Nothing to send.")
