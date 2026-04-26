from ai.task import BaseTask
import json


class NatanNotesAgent(BaseTask):
    def __init__(self, agent_model, memory):
        self.name = "NatanNotesAgent"
        self.agent_model = agent_model
        self.memory = memory

    def execute(self):
        print("NatanNotesAgent: Starting execution...")

        rozmowy = self.memory.get("rozmowy_contents")
        transakcje = self.memory.get("transakcje_contents")
        ogloszenia = self.memory.get("ogloszenia_contents")

        system_prompt = """You are a data analyst. Your task is to logically organize Natan's notes about trade.
        Extract the following information and return it as a JSON object.

        The JSON object should have the following structure:
        {
          "cities": array of strings (list of all unique city names involved in trade),
          "trade_managers": object where keys are city names and values are the full names of the people responsible for trade in that city (first and last name, if available),
          "goods_bought": object where keys are city names and values are objects. Each inner object has goods as keys and their quantities (integers) as values, representing goods bought by that city. Quantities should be 0 if not specified.
          "goods_sold": object where keys are city names and values are objects. Each inner object has goods as keys and a value of 1 (integer) if that good was sold by that city.
        }

        Example of expected output structure:
        {
          "cities": ["Brudzewo", "Celbowo"],
          "trade_managers": {
            "Brudzewo": "Rafał Kisiel",
            "Celbowo": "Oskar Radtke"
          },
          "goods_bought": {
            "Brudzewo": {
              "ryz": 55,
              "woda": 140,
              "wiertarka": 5, 
              "maka": 0,
              "chleb": 0
            },
            "Celbowo": {
              "kurczak": 40,
              "woda": 125,
              "mlotek": 6,
              "chleb": 0,
              "kapusta": 0,
              "kilof": 0
            }
          },
          "goods_sold": {
            "Brudzewo": {
              "maka": 1,
              "chleb": 1,
              "lopata": 1
            },
            "Celbowo": {
              "chleb": 1,
              "kapusta": 1,
              "kilof": 1
            }
          }
        }
        Ensure all cities and goods mentioned in the notes are included in the respective sections.
        """

        user_prompt = f"""
        Here are the notes:
        rozmowy.txt: {rozmowy}
        transakcje.txt: {transakcje}
        ogloszenia.txt: {ogloszenia}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.agent_model.chat(
            messages, response_format={"type": "json_object"}
        )

        # Clean the response from markdown
        cleaned_response = response
        if response and response.strip().startswith("```json"):
            cleaned_response = (
                response.strip().removeprefix("```json").removesuffix("```").strip()
            )

        try:
            structured_data = json.loads(cleaned_response)
            self.memory.set("structured_notes", json.dumps(structured_data, indent=2))
            print(
                f"Natan's notes have been processed and structured by the LLM. Output is: ${structured_data}"
            )
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error: Failed to decode JSON from LLM response: {e}")
            print("LLM Response was:", response)
            # Optionally, you might want to raise an exception or set a flag
            # to indicate that the structured data is not available.
