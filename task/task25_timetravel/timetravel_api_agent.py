import time
import sys
import select
import requests
import json
import re
import datetime
import os
from dotenv import load_dotenv
from ai.task import BaseTask
from ai.memory import SharedMemory
from ai.agent import Agent
from ai.tools.hub_requests import verify_answer

# Load environment variables
load_dotenv()


class TimetravelApiAgent(BaseTask):
    def __init__(self, agent: Agent, memory: SharedMemory):
        super().__init__(name="Timetravel API Agent", agent=agent, memory=memory)

    def _extract_json(self, text):
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    def execute(self) -> None:
        task_name = self.memory.get("task_name")
        print(f"Executing {self.name} for task {task_name}")

        hub_dane_url = os.environ.get("HUB_DANE_BASE_URL")
        doc_url = f"{hub_dane_url}/timetravel.md"
        response = requests.get(doc_url)
        if response.status_code == 200:
            doc = response.text
            self.memory.set("documentation", doc)
            print("Fetched documentation successfully.")
        else:
            print("Failed to fetch documentation!")
            return

        today = datetime.date.today()
        targets = [
            {"year": 2238, "month": 11, "day": 5, "tunnel": False},
            {
                "year": today.year,
                "month": today.month,
                "day": today.day,
                "tunnel": False,
            },
            {"year": 2024, "month": 11, "day": 12, "tunnel": True},
        ]

        state = {
            "api_ready": False,
            "current_internalMode": None,
            "device_state": "unknown",
            "required_PWR": 0,
            "min_internal": 0.0,
            "max_internal": 0.0,
            "pt_a": False,
            "pt_b": False,
            "current_target_index": 0,
            "targets": targets,
            "jump_completed": False,
            "battery": 100,
            "prev_battery": 3,
        }
        self.memory.set("state", state)

        help_response = verify_answer(task_name, {"action": "help"})
        print(f"API Help response: {help_response}")

        while True:
            if self.memory.get("exit_signal"):
                print("Exit signal received. Terminating API agent.")
                break

            state = self.memory.get("state")
            idx = state["current_target_index"]
            if idx >= len(targets):
                print("All jumps completed.")
                self.memory.set("exit_signal", True)
                break

            target = targets[idx]

            config_response = verify_answer(task_name, {"action": "getConfig"})
            if not isinstance(config_response, dict):
                print("Error fetching config, waiting...")
                time.sleep(2)
                continue

            print(f"Config: {config_response}")

            if "FLG:" in str(config_response):
                print(f"FLAG FOUND IN API: {config_response}")

            conf = config_response.get("config", {})
            state["device_state"] = conf.get("mode", "unknown")
            state["current_internalMode"] = conf.get("internalMode")
            state["flux_density"] = conf.get("fluxDensity", 0)

            battery_status = conf.get("batteryStatus", "3/3")
            try:
                state["battery"] = int(battery_status.split("/")[0])
            except Exception:
                state["battery"] = 3

            prev_batt = state.get("prev_battery", 3)
            current_batt = state["battery"]

            if current_batt == 3 and prev_batt < 3:
                print(
                    "\n[+] Full battery reached! Automatically advancing to the next target..."
                )
                state["jump_completed"] = True
            elif current_batt < prev_batt:
                print(
                    f"\n[!] Battery dropped from {prev_batt} to {current_batt}. Jump detected! Waiting for full charge..."
                )

            state["prev_battery"] = current_batt

            if state["battery"] == 0:
                print("Battery depleted! Resetting...")
                verify_answer(task_name, {"action": "reset"})
                state["api_ready"] = False
                self.memory.set("state", state)
                time.sleep(2)
                continue

            if state.get("jump_completed"):
                print("Jump completed according to UI.")
                state["current_target_index"] += 1
                state["api_ready"] = False
                state["jump_completed"] = False
                self.memory.set("state", state)
                time.sleep(1)
                continue

            if not state["api_ready"]:
                if state["device_state"] != "standby":
                    self.memory.set("state", state)
                    time.sleep(1)
                    continue

                print(f"Configuring target: {target}")

                prompt1 = f"Documentation:\n{doc}\n\nTarget Year: {target['year']}\nTunnel Mode: {target['tunnel']}\n\nBased on the documentation, find the required parameters for this year.\nIf Tunnel Mode is True, both pt_a and pt_b MUST be true, regardless of normal rules.\nReturn ONLY a valid JSON object with keys:\n'pwr' (integer)\n'min_internal' (float, lower bound of internalMode)\n'max_internal' (float, upper bound of internalMode)\n'pt_a' (boolean)\n'pt_b' (boolean)"

                resp1 = self.agent.chat(messages=[{"role": "user", "content": prompt1}])
                try:
                    parsed1 = self._extract_json(resp1)
                    state["required_PWR"] = parsed1["pwr"]
                    state["min_internal"] = float(parsed1["min_internal"])
                    state["max_internal"] = float(parsed1["max_internal"])
                    state["pt_a"] = parsed1["pt_a"]
                    state["pt_b"] = parsed1["pt_b"]
                    print(f"UI Params for year {target['year']}: {parsed1}")
                except Exception as e:
                    print(f"Failed to parse UI params: {resp1}, Error: {e}")
                    time.sleep(2)
                    continue

                for param in ["year", "month", "day"]:
                    verify_answer(
                        task_name,
                        {"action": "configure", "param": param, "value": target[param]},
                    )

                prompt2 = f"Documentation:\n{doc}\n\nWrite a Python function named `calculate_sync_ratio(year, month, day)` that implements the exact logic from the documentation to calculate 'syncRatio'.\nReturn ONLY the raw Python code. Do not wrap in markdown blocks, no explanations."
                resp2 = self.agent.chat(messages=[{"role": "user", "content": prompt2}])
                try:
                    code_to_exec = resp2.strip()
                    if "```" in code_to_exec:
                        match = re.search(
                            r"```(?:python)?\n?(.*?)\n?```", code_to_exec, re.DOTALL
                        )
                        if match:
                            code_to_exec = match.group(1).strip()
                        else:
                            code_to_exec = (
                                code_to_exec.replace("```python", "")
                                .replace("```", "")
                                .strip()
                            )

                    local_env = {}
                    exec(code_to_exec, {}, local_env)
                    if "calculate_sync_ratio" in local_env:
                        sync_ratio = local_env["calculate_sync_ratio"](
                            target["year"], target["month"], target["day"]
                        )
                    else:
                        # Fallback if the model used a different function name
                        func_name = [
                            k for k in local_env.keys() if callable(local_env[k])
                        ][0]
                        sync_ratio = local_env[func_name](
                            target["year"], target["month"], target["day"]
                        )

                    verify_answer(
                        task_name,
                        {
                            "action": "configure",
                            "param": "syncRatio",
                            "value": sync_ratio,
                        },
                    )
                    print(
                        f"Configured syncRatio: {sync_ratio} (using dynamically generated python function)"
                    )
                except Exception as e:
                    print(
                        f"Failed to generate or execute syncRatio function:\n{resp2}\nError: {e}"
                    )
                    time.sleep(2)
                    continue

                config = verify_answer(task_name, {"action": "getConfig"})
                hints_text = json.dumps(config, indent=2)
                help_text = (
                    json.dumps(help_response, indent=2)
                    if isinstance(help_response, dict)
                    else str(help_response)
                )

                prompt3 = (
                    f"Documentation:\n{doc}\n\n"
                    f"API /help Endpoint Docs:\n{help_text}\n\n"
                    f"Hints from API Config:\n{hints_text}\n\n"
                    f"Based on the /help endpoint instructions, the documentation, and the hints in the config, "
                    f"calculate the exact correct 'stabilization' value.\n"
                    f"Getting this right is crucial to allow 'fluxDensity' to reach 100% (an incorrect value caps it at 60%).\n"
                    f"Return ONLY a valid JSON object with a single key 'stabilization' and its value (string or number, exact)."
                )
                resp3 = self.agent.chat(messages=[{"role": "user", "content": prompt3}])
                try:
                    parsed3 = self._extract_json(resp3)
                    stabilization = parsed3["stabilization"]
                    verify_answer(
                        task_name,
                        {
                            "action": "configure",
                            "param": "stabilization",
                            "value": stabilization,
                        },
                    )
                    print(f"Configured stabilization: {stabilization}")
                except Exception as e:
                    print(f"Failed to calculate stabilization: {resp3}, Error: {e}")
                    time.sleep(2)
                    continue

                state["api_ready"] = True
                state["im_hint_shown"] = False
                self.memory.set("state", state)
                print("API configuration completed. Ready for UI jump.")

                print(f"\n--- OPERATOR ACTION REQUIRED ---")
                print(
                    f"Please MANUALLY configure the following in the UI preview before the jump:"
                )
                print(f"  > PWR:  {state['required_PWR']}")
                print(f"  > PT_A: {state['pt_a']}")
                print(f"  > PT_B: {state['pt_b']}")
                print(f"--------------------------------\n")

            else:
                # Wait for the operator to trigger the jump, and hint about internalMode
                current_im = state.get("current_internalMode")
                min_im = state.get("min_internal", 0.0)
                max_im = state.get("max_internal", 0.0)
                current_flux = state.get("flux_density", 0)

                is_im_correct = (
                    current_im is not None and min_im <= current_im <= max_im
                )
                is_flux_correct = current_flux == 100

                if is_im_correct and is_flux_correct:
                    if not state.get("im_hint_shown"):
                        print(
                            f"\n[!] HINT: internalMode ({current_im}) and fluxDensity (100%) are now CORRECT. You can perform the jump!"
                        )
                        print(
                            ">>> PRESS ENTER IN THIS TERMINAL ONCE YOU HAVE JUMPED (OR RECHARGED BATTERY) <<<"
                        )
                        state["im_hint_shown"] = True
                else:
                    state["im_hint_shown"] = False
                    if is_im_correct and not is_flux_correct:
                        print(
                            f"[!] internalMode is ready ({current_im}), but waiting for fluxDensity to reach 100% (currently: {current_flux}%)..."
                        )

                if state.get("im_hint_shown"):
                    i, o, e = select.select([sys.stdin], [], [], 0.0)
                    if i:
                        sys.stdin.readline()
                        print("\n[+] Operator manually advanced to next target!")
                        state["jump_completed"] = True

                self.memory.set("state", state)
                time.sleep(1)
