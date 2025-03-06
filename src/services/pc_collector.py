import psutil
import threading
from ..models.collector import CollectorInterface
from ..models.metric_data import MetricData

class PCCollector(CollectorInterface):
    def get_device_id(self) -> str:
        return "device_1"
    
    def get_metric_type(self) -> str:
        return "system_metrics"

    def collect(self) -> MetricData:
        ram_usage = psutil.virtual_memory().percent
        thread_count = threading.active_count()
        
        return MetricData(
            self.get_device_id(),
            self.get_metric_type(),
            {
                "ram_usage": ram_usage,
                "thread_count": thread_count
            }
        ) 