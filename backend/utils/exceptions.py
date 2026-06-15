from flask import jsonify


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def to_response(self):
        response = jsonify({'success': False, 'data': None, 'error': self.message})
        response.status_code = self.status_code
        return response


class ValidationError(APIError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
