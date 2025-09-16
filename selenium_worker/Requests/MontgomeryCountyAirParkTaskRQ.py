from json import JSONEncoder

from selenium_worker.Requests.WorkTaskRQ import WorkTaskRQ


class MontgomeryCountyAirParkTaskRQ(WorkTaskRQ):
    FirstName: str = ''
    LastName: str = ''
    EmailAddress: str = ''
    PhoneNumber: str = ''
    StreetAddress: str = ''
    CityAddress: str = ''
    StateAddress: str = ''
    ZIPAddress: str = ''
    AirportSourceNameCode: str = ''
    StartDate: str = ''
    EndDate: str = ''
    StartTime: str = ''
    EndTime: str = ''
    AircraftType: str = ''
    DescriptionOrQuestion: str = ''
    ResponseRequested: str = ''

    def validate(self) -> list[str]:
        Errors = []

        if not self.FirstName:
            Errors.append('Missing `FirstName` value')
        if not self.LastName:
            Errors.append('Missing `LastName` value')
        if not self.EmailAddress:
            Errors.append('Missing `EmailAddress` value')
        if not self.PhoneNumber:
            Errors.append('Missing `PhoneNumber` value')
        if not self.StreetAddress:
            Errors.append('Missing `StreetAddress` value')
        if not self.CityAddress:
            Errors.append('Missing `CityAddress` value')
        if not self.StateAddress:
            Errors.append('Missing `StateAddress` value')
        if not self.ZIPAddress:
            Errors.append('Missing `ZIPAddress` value')
        if not self.StartDate:
            Errors.append('Missing `StartDate` value')
        if not self.EndDate:
            Errors.append('Missing `EndDate` value')
        if not self.StartTime:
            Errors.append('Missing `StartTime` value')
        if not self.EndTime:
            Errors.append('Missing `EndTime` value')
        if not self.AircraftType:
            Errors.append('Missing `AircraftType` value')
        if not self.DescriptionOrQuestion:
            Errors.append('Missing `DescriptionOrQuestion` value')
        if not self.ResponseRequested:
            Errors.append('Missing `ResponseRequested` value')

        return Errors


class MontgomeryCountyAirParkTaskRQEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
