from abc import ABC, abstractmethod
from arklex.env.exceptions import FunctionCallError
from arklex.utils.graph_state import MessageState


def register_worker(cls):
    """Decorator to register a worker."""
    cls.name = cls.__name__  # Automatically set name to the class name
    return cls


class BaseWorker(ABC):
    
    description = None

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"{self.__class__.__name__}"
    
    def worker_call(self, func):
        """Perform worker call and return (response: string, is_completed: bool)"""
        try:
            response_state = func()
            return response_state, True
        except FunctionCallError as e:
            return str(e), False
        except Exception as e:
            return str(e), False
        
    @abstractmethod
    def execute(self, msg_state: MessageState):
        pass
