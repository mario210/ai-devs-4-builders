import os
import sys

# Ensure the parent directory is in the path so we can import the original Agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import Agent
from ai.orchestrator import AgentOrchestrator
from ai.task import BaseTask


# --- Define Specific Tasks ---

class ResearchTask(BaseTask):
    """A specialized task/agent for gathering data."""

    def execute(self) -> None:
        prompt = "Provide 3 short, interesting facts about quantum computing. Format as a simple list."

        print(f"\n--- [{self.name}] Gathering Information ---")
        response = self.agent.chat(messages=[{"role": "user", "content": prompt}])

        print(f"[{self.name}] Output:\n{response}")

        # Write result to shared memory for the next agent
        self.memory.set("quantum_facts", response)


class SummaryTask(BaseTask):
    """A specialized task/agent for analyzing data produced by other agents."""

    def execute(self) -> None:
        # Read data from shared memory
        facts = self.memory.get("quantum_facts")

        if not facts:
            print(f"[{self.name}] Error: No facts found in shared memory!")
            return

        prompt = f"Take the following facts and summarize them into exactly ONE sentence:\n{facts}"

        print(f"\n--- [{self.name}] Summarizing Data ---")
        response = self.agent.chat(messages=[{"role": "user", "content": prompt}])

        print(f"[{self.name}] Output:\n{response}")
        self.memory.set("final_summary", response)


def main():
    # 1. Initialize the Main Orchestrator
    # You can pass a main Agent here if the orchestrator itself needs to make routing decisions
    orchestrator_main_agent = Agent(default_model="openai/gpt-4o") # Use a capable model for synthesis
    orchestrator = AgentOrchestrator(main_agent=orchestrator_main_agent)

    # 2. Instantiate Agents for specific roles (using your existing agent.py)
    research_agent = Agent(default_model="openai/gpt-4o-mini")
    writer_agent = Agent(default_model="openai/gpt-4o")

    # 3. Create tasks, assigning them their specific agents and the orchestrator's shared memory
    orchestrator.add_task(ResearchTask(name="FactFinder", agent=research_agent, memory=orchestrator.memory))
    orchestrator.add_task(SummaryTask(name="ExecutiveSummarizer", agent=writer_agent, memory=orchestrator.memory))

    # 4. Run the coordinated workflow
    orchestrator.run()


if __name__ == "__main__":
    main()