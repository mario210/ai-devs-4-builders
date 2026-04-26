from ai.tools.files import read_file_content
from ai.task import BaseTask


class FileReaderAgent(BaseTask):
    """
    Agent that reads the content of a specified file and stores it in shared memory.

    This agent is responsible for reading a file whose path is provided during
    initialization. The content of the file is then stored in shared memory
    under the key specified by `content_key` for other agents to access.
    """
    def __init__(self, agent_model, memory, content_key: str, file_path: str):
        """
        Initializes the FileReaderAgent.

        Args:
            agent_model: The model associated with this agent (if any).
            memory: The shared memory instance to store the file content.
            content_key: The key under which the file content will be stored in memory.
            file_path: The absolute path to the file to be read.
        """
        super().__init__("FileReaderAgent", agent_model, memory)
        self.content_key = content_key
        self.file_path = file_path

    def execute(self) -> None:
        """
        Executes the file reading task.

        Reads the content of the file specified by `self.file_path` and
        stores it in `self.memory` with the key `self.content_key`.
        """
        content = read_file_content(self.file_path)
        self.memory.set(self.content_key, content)
