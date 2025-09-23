from json import JSONEncoder

class ComplaintTaskRS:
    Errors = []
    Logs = []
    State: int = 0

    def __init__(self):
        pass

class ComplaintTaskRSEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
