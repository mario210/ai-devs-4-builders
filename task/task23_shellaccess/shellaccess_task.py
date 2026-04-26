from loguru import logger
import json
from pathlib import Path
from ai.task import BaseTask
from ai.memory import SharedMemory
from ai.tools import definition


class ShellAccessTask(BaseTask):

    def __init__(self, agent_model, memory: SharedMemory):
        super().__init__(memory.get("task_name"), agent_model, memory)
        self.agent_model = agent_model

    def execute(self):
        prompt = (
            Path(__file__)
            .parent.parent.parent.joinpath("task", "task23_shellaccess/prompt.md")
            .read_text(encoding="utf-8")
        )

        system_prompt = """
You are an AI assistant designed to interact with a shell command verification tool.
When using the `run_shell_command_v2` tool, pay close attention to the tool's output. If you receive an error message that includes "Invalid value in field 'date'", it means the date you provided was incorrect or not accepted by the system.

**Crucially, do NOT retry the exact same date again.**

Instead, you must re-evaluate the date based on the task's requirements. If the task involves a specific date calculation, such as subtracting exactly one day from an original date, ensure you apply that rule correctly before attempting verification again. Your next attempt with the `date` field must use a *different*, corrected date.
"""

        final_agent_response = self.agent.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            tools=definition.SHELL_TOOLS,
            tool_map=definition.SHELL_TOOLS_MAP,
            max_iterations=30,
        )
        logger.info("Agent has completed its work.")
        print(final_agent_response)
