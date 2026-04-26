from abc import ABC, abstractmethod
from .memory import SharedMemory

class BaseTask(ABC):
    """
    Abstract base class for all ai tasks.
    Each task represents a step in the workflow and wraps its own Agent.
    """
    def __init__(self, name: str, agent, memory: SharedMemory):
        self.name = name
        self.agent = agent
        self.memory = memory

    @abstractmethod
    def execute(self) -> None:
        """Execute the task. Must be implemented by subclasses.
        Agents should read from and write to self.memory within this method."""
        pass