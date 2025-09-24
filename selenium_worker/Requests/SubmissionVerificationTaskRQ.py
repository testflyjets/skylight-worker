from json import JSONEncoder
from selenium_worker import config as cfg

class SubmissionVerificationTaskRQ:
    ApiKey: str = cfg.AirnoiseSettings.SUBMISSION_VERIFIER_API_KEY
    Id: str = ''
    SubmissionVerified: bool = False
    SubmitterIp: str = ''
    SubmissionError: str = ''
    ErrorBacktrace: str = ''
    SubmissionDetails: dict = None

    def __init__(self, j: dict):
        # Set default for SubmissionDetails before updating from dict
        if self.SubmissionDetails is None:
            self.SubmissionDetails = {}
        if j != '':
            self.__dict__.update(j)
        # Ensure SubmissionDetails is always a dict after initialization
        if not isinstance(self.SubmissionDetails, dict):
            self.SubmissionDetails = {}

    def validate(self) -> list[str]:
        Errors = []

        if not self.ApiKey:
            Errors.append('Missing `ApiKey` value')
        if not self.Id:
            Errors.append('Missing `Id` value')
        if self.SubmissionVerified is None:
            Errors.append('Missing `SubmissionVerified` value')
        if not self.SubmitterIp:
            Errors.append('Missing `SubmitterIp` value')

        return Errors

    def to_snake_case_dict(self) -> dict:
        """Convert PascalCase properties to snake_case for Ruby API submission"""
        return {
            'api_key': self.ApiKey,
            'id': self.Id,
            'submission_verified': self.SubmissionVerified,
            'submitter_ip': self.SubmitterIp,
            'submission_error': self.SubmissionError,
            'error_backtrace': self.ErrorBacktrace,
            'submission_details': self.SubmissionDetails
        }

    def to_request_body(self) -> dict:
        """Convert to JSON API request body format for Ruby API submission"""
        return {
            'data': {
                'type': 'airnoise_complaint',
                'attributes': {
                    'api_key': self.ApiKey,
                    'id': self.Id,
                    'submission_verified': self.SubmissionVerified,
                    'submitter_ip': self.SubmitterIp,
                    'submission_error': self.SubmissionError,
                    'error_backtrace': self.ErrorBacktrace,
                    'submission_details': self.SubmissionDetails
                }
            }
        }


class SubmissionVerificationTaskRQEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
