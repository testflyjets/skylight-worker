from json import JSONEncoder

class ComplaintTaskRQ:
    Type: str = ''
    SessionUID: str = ''
    
    # Complaint-specific fields
    ComplaintType: str = ''
    AirportIdent: str = ''
    TimeZone: str = ''
    Title: str = ''
    FirstName: str = ''
    LastName: str = ''
    Email: str = ''
    Phone: str = ''
    Street: str = ''
    ParsedStreet: str = ''
    City: str = ''
    State: str = ''
    Zip: str = ''
    Comments: str = ''
    EventTime: str = ''
    Remarks: str = ''
    AirnoiseCategory: str = ''
    Registration: str = ''
    AircraftType: str = ''
    EngineCount: int = 0
    AircraftModel: str = ''
    Operator: str = ''
    Callsign: str = ''
    OperationType: str = ''
    Altitude: int = 0
    Airspeed: int = 0
    DirectionOfFlight: str = ''
    RequestReplyToComplaint: bool = False
    ApiKey: str = ''
    CallbackUrl: str = ''

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
        if not self.ComplaintType:
            Errors.append('Missing `ComplaintType` value')
        if not self.AirportIdent:
            Errors.append('Missing `AirportIdent` value')
        if not self.TimeZone:
            Errors.append('Missing `TimeZone` value')
        if not self.Title:
            Errors.append('Missing `Title` value')
        if not self.FirstName:
            Errors.append('Missing `FirstName` value')
        if not self.LastName:
            Errors.append('Missing `LastName` value')
        if not self.Email:
            Errors.append('Missing `Email` value')
        if not self.Phone:
            Errors.append('Missing `Phone` value')
        if not self.Street:
            Errors.append('Missing `Street` value')
        if not self.City:
            Errors.append('Missing `City` value')
        if not self.State:
            Errors.append('Missing `State` value')
        if not self.Zip:
            Errors.append('Missing `Zip` value')
        if not self.EventTime:
            Errors.append('Missing `EventTime` value')
        if not self.AirnoiseCategory:
            Errors.append('Missing `AirnoiseCategory` value')
        if not self.Registration:
            Errors.append('Missing `Registration` value')
        if not self.AircraftType:
            Errors.append('Missing `AircraftType` value')
        if not self.AircraftModel:
            Errors.append('Missing `AircraftModel` value')
        if not self.Operator:
            Errors.append('Missing `Operator` value')
        if not self.Callsign:
            Errors.append('Missing `Callsign` value')
        if not self.OperationType:
            Errors.append('Missing `OperationType` value')
        if not self.Altitude:
            Errors.append('Missing `Altitude` value')
        if not self.Airspeed:
            Errors.append('Missing `Airspeed` value')
        if not self.DirectionOfFlight:
            Errors.append('Missing `DirectionOfFlight` value')
        if not self.CallbackUrl:
            Errors.append('Missing `CallbackUrl` value')

        return Errors

class ComplaintTaskRQEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
