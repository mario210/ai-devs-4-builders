from loguru import logger
from typing import List
from .memory import SharedMemory
from .task import BaseTask

class AgentOrchestrator:
    """
    Main orchestrator that manages shared memory and executes tasks.
    Can act simply as a pipeline manager, or use a 'main_agent' to synthesize results.
    """
    def __init__(self, main_agent=None):
        self.memory = SharedMemory()
        self.main_agent = main_agent  # Optional: if the orchestrator needs its own brain
        self.tasks: List[BaseTask] = []

    def add_task(self, task: BaseTask) -> None:
        """Register a new task in the workflow."""
        self.tasks.append(task)

    def run(self) -> None:
        """Execute all registered tasks sequentially."""
        logger.debug("Starting Multi-Agent Orchestrator Workflow...")
        
        for task in self.tasks:
            logger.debug(f"Executing Task: [{task.name}]")
            try:
                task.execute()
            except Exception as e:
                logger.error(f"Workflow interrupted! Task '{task.name}' failed: {e}")
                break
                
        logger.debug("Workflow execution finished.")
        
        # If a main_agent is provided, it can synthesize results from shared memory
        if self.main_agent:
            logger.debug("Main Agent synthesizing final results from shared memory...")
            
            # Get all current memory content.
            # ASSUMPTION: SharedMemory has a 'get_all()' method that returns a dict.
            # If not, you would need to implement it in your memory.py.
            memory_content = self.memory.get_all() 
            
            if memory_content:
                synthesis_prompt = (
                    "You are the main orchestrator agent. Your sub-agents have completed their tasks "
                    "and stored information in shared memory. Review the following data from shared memory "
                    "and provide a concise, human-readable summary of the overall findings or outcome:\n\n"
                    f"Shared Memory Content:\n{memory_content}"
                )
                
                final_report = self.main_agent.chat(messages=[{"role": "user", "content": synthesis_prompt}])
                
                if final_report:
                    logger.info("\n--- Main Agent's Final Report ---")
                    print(final_report) # This is the "communication with human"
                    logger.info("---------------------------------")
                else:
                    logger.warning("Main Agent failed to generate a final report.")
            else:
                logger.info("No content found in shared memory for main agent to synthesize.")

        # If orchestrator uses a shared agent, print its stats
        if self.main_agent and hasattr(self.main_agent, 'print_usage_statistics'):
            self.main_agent.print_usage_statistics()
