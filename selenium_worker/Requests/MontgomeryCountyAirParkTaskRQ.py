from json import JSONEncoder

from selenium_worker.Requests.WorkTaskRQ import WorkTaskRQ
from selenium_worker.utils import get_date


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
    StartTime: str = ''
    AircraftType: str = ''
    DescriptionOrQuestion: str = ''
    ResponseRequested: str = ''

    # Computed properties (will be set in __init__)
    startDateTime: str = ''
    hiddenStartDateTime: str = ''

    def __init__(self, j: dict):
        # Call parent constructor first
        super().__init__(j)

        # Compute derived properties
        self._compute_properties()

    def _compute_properties(self):
        """Compute derived properties based on the current field values."""
        # Compute start date/time properties
        start_date = get_date(self.StartDate)
        if start_date is not None:
            self.startDateTime = start_date.strftime('%d-%m-%Y') + ' ' + self.StartTime
            self.hiddenStartDateTime = start_date.strftime('%m/%d/%Y') + ' ' + self.StartTime
        else:
            self.startDateTime = ''
            self.hiddenStartDateTime = ''

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
        if not self.AirportSourceNameCode:
            Errors.append('Missing `AirportSourceNameCode` value')
        if not self.StartDate:
            Errors.append('Missing `StartDate` value')
        if not self.StartTime:
            Errors.append('Missing `StartTime` value')
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
