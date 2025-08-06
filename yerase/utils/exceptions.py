from rest_framework.views import exception_handler
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and 'detail' in response.data:
        if response.data['detail'] == 'Authentication credentials were not provided.':
            response.data = {
                'result': 'error',
                'message': 'please log to your account'
            }
            response.status_code = status.HTTP_401_UNAUTHORIZED 

    return response

class EmailDuplicationException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_409_CONFLICT):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class UsernameDuplicationException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_409_CONFLICT):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class InvalidAdminCredentialsException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_403_FORBIDDEN):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class AdminAccountNotFound(Exception):
    def __init__(self, message, data=None, code=status.HTTP_404_NOT_FOUND):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data
    
class ValidationException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class UUIDException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class WrongPasswordException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_406_NOT_ACCEPTABLE):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data
    
class PasswordMismatchException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_409_CONFLICT):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class BaseClassSerializerException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data
    

class CategoryNameDuplicationException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_409_CONFLICT):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class TitleDuplicationException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_409_CONFLICT):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class DuplicationException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_409_CONFLICT):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class ValueErrorException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        return self.message, self.data

class ValueDuplicationException(Exception):
    def __init__(self, message, data=None, code=status.HTTP_409_CONFLICT):
        self.message = message
        self.data = data
        self.code = code
        super().__init__(message, data)

    def __str__(self):
        if self.data:
            return f"{self.message} - Data: {self.data}"
        return self.message

