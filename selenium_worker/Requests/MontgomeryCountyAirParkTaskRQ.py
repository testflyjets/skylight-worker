from json import JSONEncoder
from datetime import datetime
from typing import Optional

from selenium_worker.Requests.ComplaintTaskRQ import ComplaintTaskRQ


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


class MontgomeryCountyAirParkTaskRQ(ComplaintTaskRQ):
    # Computed properties (will be set in __init__)
    StartDateTime: str = ''
    HiddenStartDateTime: str = ''

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
            self.StartDateTime = event_datetime.strftime('%d-%m-%Y %H:%M')
            self.HiddenStartDateTime = event_datetime.strftime('%m/%d/%Y %H:%M')
        else:
            self.StartDateTime = ''
            self.HiddenStartDateTime = ''

class MontgomeryCountyAirParkTaskRQEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
