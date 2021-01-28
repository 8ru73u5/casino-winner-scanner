from json import dumps


class InvalidApiResponseError(Exception):
    def __init__(self, api_response: dict, exception: Exception = None):
        super().__init__()
        self.api_response = api_response
        self.message = f' ({exception})' if exception is not None else ''

    def __str__(self):
        return f'Casino Winner API returned unexpected response{self.message}:\n{dumps(self.api_response, ensure_ascii=False, indent=2)}'
