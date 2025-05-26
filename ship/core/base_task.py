from abc import ABC, abstractmethod
from typing import Any

class BaseTask(ABC):
    """Base class for all Tasks in Porto architecture"""

    def __init__(self, **dependencies):
        self.dependencies = dependencies

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Execute the task"""
        pass