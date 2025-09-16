from json import JSONEncoder

from selenium_worker.Responses.WorkTaskRS import WorkTaskRS


class MontgomeryCountyAirParkTaskRS(WorkTaskRS):
    pass

class MontgomeryCountyAirParkTaskRSEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
