import threading

class UploaderQueue:
    def __init__(self):
        self.queue = []
        self._lock = threading.Lock()

    def add(self, data):
        with self._lock:
            self.queue.append(data)

    def get_all(self):
        with self._lock:
            data = self.queue.copy()
            self.queue.clear()
            return data 