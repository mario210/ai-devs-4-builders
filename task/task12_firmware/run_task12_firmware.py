import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import re

# Ensure the AI_Devs4 root directory is in the path to import custom modules
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from ai.tools.definition import SHELL_TOOLS, SHELL_TOOLS_MAP
from ai.tools.hub_requests import verify_answer
from ai.agent import Agent
from ai.orchestrator import AgentOrchestrator
from ai.task import BaseTask


class FirmwareTask(BaseTask):
    """Task responsible for fixing and running the firmware."""

    def execute(self) -> None:
        print(f"[{self.name}] Starting firmware task...")

        system_prompt = """You are an expert Linux administrator working in a very restricted environment. 
Your goal is to successfully run /opt/firmware/cooler/cooler.bin and get the special ECCS-xxx code.
The shell you have access to is highly non-standard. Always start by using the `help` command to understand what commands are available.
You are running under a regular user account.
You MUST NOT look into /etc, /root, or /proc/ directories. 
You MUST respect .gitignore files - always read them first and NEVER read or touch files/directories listed in them (such as .env, storage.cfg, logs).
The filesystem is mostly read-only, but the volume with the firmware allows writing.

To run a shell command, you must use the `run_shell_command` tool provided to you. It will execute the command and return the output.
If you get a security policy violation or ban, DO NOT repeat the forbidden command. Read the error carefully and try a different approach.
If the error tells you 'reboot': True, you should use the `run_shell_command` with the `reboot` command to reset the environment state.

Steps to take:
1. Discover the available commands by running `help`.
2. Find out how to edit files if standard tools are not available.
3. Find the password for the firmware. It is saved in several places in the system.
4. Reconfigure the firmware (settings.ini) so it works correctly.
5. Run /opt/firmware/cooler/cooler.bin and capture the output.
6. Look for a string starting with ECCS- in the output. This is the code.
7. Return the final code when you find it.
8. At the end, please describe step by step what you did to reach the ECCS code.

Analyze the errors if the firmware fails to run and adapt your strategy.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Start your investigation and get the ECCS- code.",
            },
        ]

        # In the chat method of the provided agent, it expects a list of dictionaries with 'role' and 'content',
        # and tools passed as 'tools', and functions passed as 'tool_map'
        response = self.agent.chat(
            messages=messages,
            tools=SHELL_TOOLS,
            tool_map=SHELL_TOOLS_MAP,
            max_iterations=50,  # Need high number of iterations for this task
        )

        print(f"[{self.name}] Agent final response: {response}")

        if not response:
            print(f"[{self.name}] Agent returned empty response.")
            return

        # Assuming the agent returns the code in the final response
        code = None
        match = re.search(r"ECCS-[a-fA-F0-9]{40}", response)
        if match:
            code = match.group(0)

        if code:
            print(f"[{self.name}] Extracted code: {code}")
            verification_response = verify_answer("firmware", {"confirmation": code})
            print(f"[{self.name}] Verification response: {verification_response}")
        else:
            print(f"[{self.name}] Failed to extract code from agent's response.")


def run_task12_firmware(agent_model):
    shared_agent = Agent(default_model=agent_model)

    orchestrator = AgentOrchestrator()
    orchestrator.add_task(
        FirmwareTask(name="Firmware", agent=shared_agent, memory=orchestrator.memory)
    )

    orchestrator.run()

    shared_agent.print_usage_statistics()


if __name__ == "__main__":
    run_task12_firmware("anthropic/claude-sonnet-4.6")
