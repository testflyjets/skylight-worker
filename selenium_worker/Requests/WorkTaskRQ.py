from json import JSONEncoder


class WorkTaskRQ:
    Type: str = ''
    SessionUID: str = ''
    
    # Task retry parameters
    Countdown: int = 0
    DefaultRetryDelay: int = 10
    MaxRetries: int = 3
    RetryBackoff = True
    RetryBackoffMax = 600
    RetryJitter = True

    def __init__(self, j: dict):
        if j != '':
            self.__dict__.update(j)

    def validate(self) -> list[str]:
        Errors = []
        if not self.Type:
            Errors.append('Missing `Type` value')

        return Errors


class WorkTaskRQEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
