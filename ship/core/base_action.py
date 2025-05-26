from abc import ABC, abstractmethod
from typing import Any


class BaseAction(ABC):
    """Base class for all Actions in Porto architecture"""

    def __init__(self, **dependencies):
        self.dependencies = dependencies

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Execute the action"""
        pass