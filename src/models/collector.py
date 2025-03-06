from abc import ABC, abstractmethod
from .metric_data import MetricData

class CollectorInterface(ABC):
    @abstractmethod
    def get_device_id(self) -> str:
        pass

    @abstractmethod
    def get_metric_type(self) -> str:
        pass
    
    @abstractmethod
    def collect(self) -> MetricData:
        pass 