import threading
import datetime
import time
import heapq



class JobQueue:
    def __init__(self):
        self.jobs = []
        self.jobs_dict = {}

        self.lock = threading.Lock()
        self.stop_event = threading.Event()


    def __del__(self):
        try:
            self.sleep()
        except Exception as error:
            print(error)


    def add_job(self, uuid: str, tasks: list, timeout: int):
        with self.lock:
            timeout_timestamp = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
            heapq.heappush(self.jobs, (timeout_timestamp, uuid, tasks))
            self.jobs_dict[uuid] = tasks

        self.wake()


    def execute_job(self, uuid: str, tasks_consumer, *args, **kwargs):
        if self.jobs:
            tasks = self.jobs_dict.pop(uuid, [])

            if tasks:
                return tasks_consumer(tasks, *args, **kwargs)
            

    def wake(self):
        if getattr(self, 'timeout_thread', None) is None:
            self.timeout_thread = threading.Thread(target=self._watch_jobs)
            self.timeout_thread.daemon = True
            self.stop_event.clear()
            self.timeout_thread.start()
    

    def sleep(self):
        if getattr(self, 'timeout_thread', None) is not None:
            print("Sleeping...")
            self.stop_event.set()
            self.timeout_thread.join()


    def _watch_jobs(self):
        while not self.stop_event.is_set():
            with self.lock:
                if self.jobs:
                    while self.jobs and self.jobs[0][0] <= datetime.datetime.now():
                        _, uuid, _ = heapq.heappop(self.jobs)
                        del self.jobs_dict[uuid]
                        print(f"Job {uuid} timed out.")
                else:
                    self.sleep()

                time.sleep(1)
