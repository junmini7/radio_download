import random
class KBS:
    def __init__(self):
        self.record_schedules = None
        self.update_schedules()

    def update_schedules(self):
        from collections import defaultdict
        schedules_data = defaultdict(list)
        schedules_data[0].append(random.random())
        self.record_schedules = schedules_data
