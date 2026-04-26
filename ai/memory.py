import threading
from typing import Any, Dict

class SharedMemory:
    """Thread-safe centralized memory store for agents to share context and state."""
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from shared memory."""
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store a value in shared memory."""
        with self._lock:
            self._state[key] = value

    def get_all(self) -> Dict[str, Any]:
        """Return a copy of the entire memory state."""
        with self._lock:
            return self._state.copy()