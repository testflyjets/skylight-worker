from json import JSONEncoder

from selenium_worker.Responses.ComplaintTaskRS import ComplaintTaskRS


class MontgomeryCountyAirParkTaskRS(ComplaintTaskRS):
    pass

class MontgomeryCountyAirParkTaskRSEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
