import time

class MetricData:
    def __init__(self, device_id: str, metric_type: str, values: dict):
        self.device_id = device_id
        self.metric_type = metric_type
        self.values = values
        self.timestamp = time.time()

    def __str__(self):
        return f"MetricData(device_id={self.device_id}, type={self.metric_type}, values={self.values})" 