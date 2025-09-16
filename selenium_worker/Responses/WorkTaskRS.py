from json import JSONEncoder


class WorkTaskRS:
    Errors = []
    Logs = []
    State: int = 0

    def __init__(self):
        pass

class WorkTaskRSEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
