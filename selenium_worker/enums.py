from enum import Enum, StrEnum

class BrowserDriverType(Enum):
    Unknown = 0
    Chrome = 1

class ProxyVariation(StrEnum):
    DISABLED = 'DISABLED'
    INCLUSIVE = 'INCLUSIVE'
    EXCLUSIVE = 'EXCLUSIVE'

class WorkerType(Enum):
    Unknown = "UNKNOWN"
    Montgomery = "KGAI"
    FAA = "FAA"