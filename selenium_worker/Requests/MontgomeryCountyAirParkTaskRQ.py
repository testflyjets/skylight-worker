from json import JSONEncoder
from datetime import datetime
from typing import Optional

from selenium_worker.Requests.WorkTaskRQ import WorkTaskRQ


def parse_event_time(event_time_str: str) -> Optional[datetime]:
    """
    Parse an EventTime string in the format "2025-09-20 10:23:40 -0700"
    Returns a datetime object or None if parsing fails.
    """
    if not event_time_str:
        return None

    # Common formats for EventTime
    formats = [
        '%Y-%m-%d %H:%M:%S %z',  # "2025-09-20 10:23:40 -0700"
        '%Y-%m-%d %H:%M:%S',     # "2025-09-20 10:23:40" (no timezone)
        '%m/%d/%Y %H:%M:%S',     # "09/20/2025 10:23:40"
        '%m-%d-%Y %H:%M:%S',     # "09-20-2025 10:23:40"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(event_time_str, fmt)
        except ValueError:
            continue

    return None


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
    EventTime: str = ''
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
        # Parse the EventTime field
        event_datetime = parse_event_time(self.EventTime)
        if event_datetime is not None:
            # Format for the form fields (same format as before)
            self.startDateTime = event_datetime.strftime('%d-%m-%Y %H:%M:%S')
            self.hiddenStartDateTime = event_datetime.strftime('%m/%d/%Y %H:%M:%S')
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
        if not self.EventTime:
            Errors.append('Missing `EventTime` value')
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
