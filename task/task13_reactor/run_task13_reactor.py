import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import json
import time

# Ensure the AI_Devs4 root directory is in the path to import custom modules
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from ai.tools.hub_requests import verify_answer
from ai.agent import Agent


def send_command(cmd):
    res = verify_answer("reactor", {"command": cmd})
    return res


class ReactorAgentController:
    def __init__(self, agent_model):
        self.agent = Agent(default_model=agent_model)
        self.mistake_history = []  # Contextual feedback from previous failures
        self.attempt = 1
        self.turn = 1
        self.last_action = None
        self.last_state = None
        self.messages = []

    def get_system_prompt(self):
        base_prompt = """You are a system controlling a robot (P) in a reactor.
The map consists of 7 columns (0-6) and 5 rows (0-4).
The robot is always located in row Y=4 (the lowest level). You start at X=0, Y=4.
You must reach the destination point at X=6, Y=4.

Game rules:
1. Your allowed actions are "left", "right" and "wait". You must choose EXACTLY ONE in each step.
2. There are reactor blocks 'B' on the board that move vertically. Each block has a height of 2 fields (occupies 2 dots).
3. If the bottom edge of a block reaches row Y=4 and you are there, you will be crushed.
4. The blocks move up or down alternately.
5. Pay attention to the JSON arrays with information from the server - you may receive the movement directions of specific columns containing blocks, and the current position of the robot.
6. Your task is to predict, based on the received map (in the `map` array or as part of the `message`), where the blocks will be based on their current position, their potential direction (e.g., "direction": "down") and the following logic:
   - If a block is moving down, its Y will increase by 1 (if possible).
   - If the bottom of a block is at Y=3, and it is moving down, in the next round its bottom will reach Y=4 and crush anything standing in that column!

Analyze the JSON structure every time. The API returns, among other things, the "map" key, or the map and other information are located in the "message". Pay attention to everything.
Return your response in JSON format containing:
- "analysis": Your conclusions and in-depth analysis of the situation (where you are, if there is a block in the way, what will happen after each of the 3 available moves).
- "command": Your choice ("left", "right" or "wait").
"""
        # Inject contextual feedback / Learning from mistakes
        if self.mistake_history:
            base_prompt += "\n\n=== MISTAKE MEMORY (From contextual feedback) ===\n"
            base_prompt += "Learn from the following mistakes from previous attempts and DO NOT repeat them:\n"
            for i, mistake in enumerate(self.mistake_history, 1):
                base_prompt += f"{i}. {mistake}\n"

        return base_prompt

    def on_start(self):
        """Hook called when starting or restarting the task"""
        print(f"\n[HOOK: onStart] Starting attempt #{self.attempt}...")
        res = send_command("start")
        self.turn = 1
        self.messages = [{"role": "system", "content": self.get_system_prompt()}]
        return res

    def on_error(self, res):
        """Hook called when the robot is crushed - Contextual Feedback implementation"""
        print("\n[HOOK: onError] Smashed! Learning from mistakes...")

        # Remember the mistake context to learn from it
        mistake_context = (
            f"In attempt {self.attempt}, turn {self.turn}, the last action taken was '{self.last_action}'. "
            f"This move led to getting crushed by a reactor block. Pay closer attention to the Y position of blocks "
            f"above the robot before deciding to move or wait."
        )
        self.mistake_history.append(mistake_context)
        print(f"Added to mistake memory: {mistake_context}")

        self.attempt += 1
        return self.on_start()  # Autonomously restart

    def on_finish(self, res):
        """Hook called when the task is successfully completed"""
        print("\n[HOOK: onFinish] SUCCESS! Flag captured.")
        print(json.dumps(res, indent=2))
        self.agent.print_usage_statistics()

    def extract_action(self, response_text):
        """Extracts the 'left', 'right', 'wait' command robustly."""
        try:
            if isinstance(response_text, dict):
                parsed = response_text
            else:
                text = str(response_text).strip()
                # Remove markdown code blocks if present
                if text.startswith("```json"):
                    text = text[7:-3].strip()
                elif text.startswith("```"):
                    text = text[3:-3].strip()

                try:
                    parsed = json.loads(text)
                except Exception:
                    import ast

                    parsed = ast.literal_eval(text)

                # Handle double-encoded JSON strings
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)

            if isinstance(parsed, dict):
                # Force lower case on keys and the command value to handle unexpected casing
                parsed_lower = {str(k).lower(): v for k, v in parsed.items()}
                action = str(parsed_lower.get("command", "wait")).strip().lower()
            else:
                action = "wait"

            if action not in ["left", "right", "wait"]:
                action = "wait"
        except Exception as e:
            print(f"Error during parsing of response from LLM (json): {e}")
            # Ultimate fallback: Extract the command using regex if JSON and AST parsing fail
            import re

            match = re.search(
                r"['\"]command['\"]\s*:\s*['\"](left|right|wait)['\"]",
                str(response_text),
                re.IGNORECASE,
            )
            if match:
                action = match.group(1).lower()
            else:
                action = "wait"
        return action

    def run(self):
        res = self.on_start()

        while True:
            print(f"\n=== Attempt {self.attempt} | Turn {self.turn} ===")

            msg = res.get("message", "")
            if isinstance(msg, str) and "flg" in msg.lower():
                self.on_finish(res)
                break

            if res.get("error"):
                res = self.on_error(res)
                continue

            if "code" in res and res.get("code") not in [0, 100]:
                print("[FATAL ERROR] API Error or Failed state!")
                print(json.dumps(res, indent=2))
                break

            prompt = f"Turn {self.turn}. Current response from the server after the last move (with map and parameters):\n{json.dumps(res)}\nSelect next move and return JSON."
            self.messages.append({"role": "user", "content": prompt})

            print("Asking LLM for the next move (Context-Aware)...")
            response_text = self.agent.chat(
                messages=self.messages, response_format={"type": "json_object"}
            )

            if not response_text:
                print("Error: empty response from LLM.")
                break

            print(f"LLM Response: {response_text}")
            self.messages.append({"role": "assistant", "content": response_text})

            action = self.extract_action(response_text)
            self.last_action = action
            self.last_state = res

            print(f"Selected action: {action}")
            time.sleep(1)
            res = send_command(action)
            self.turn += 1


def run_task13_reactor(agent_model):
    print("Starting reactor task with LLM (Contextual Feedback Architecture)...")
    controller = ReactorAgentController(agent_model)
    controller.run()


if __name__ == "__main__":
    run_task13_reactor("google/gemini-3-flash-preview")
