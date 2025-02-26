# Base Exception
class FunctionCallError(Exception):
    """Base exception for all errors related to LLM function or tool calls."""
    def __init__(self, message: str = None):
        if message is None:
            message = "An error occurred during an LLM function or tool call."
        super().__init__(message)


class FunctionFailureError(FunctionCallError):
    """Raised when a function fails to perform its intended action."""
    def __init__(self, message: str = None):
        if message is None:
            message = "The function failed to perform as expected."
        super().__init__(message)


class OutputError(FunctionCallError):
    """Raised when the output is not the one expected."""
    def __init__(self, message: str = None):
        if message is None:
            message = "The output is not expected."
        super().__init__(message)

class DataNotFoundError(FunctionCallError):
    """Raised when expected data is not found."""
    def __init__(self, message: str = None):
        if message is None:
            message = "Expected data was not found."
        super().__init__(message)


class ParameterMissingError(FunctionCallError):
    """Raised when there is a missing parameter."""
    def __init__(self, parameter: str, message: str = None):
        if message is None:
            message = f"The required parameter '{parameter}' is missing."
        super().__init__(message)
        self.parameter = parameter


class ParameterMismatchError(FunctionCallError):
    """Raised when the parameters provided do not match the expected schema or types."""
    def __init__(self, parameter: str, expected: str, received: str, message: str = None):
        if message is None:
            message = (f"Parameter '{parameter}' mismatch: expected type/schema '{expected}', "
                       f"but received '{received}'.")
        super().__init__(message)
        self.parameter = parameter
        self.expected = expected
        self.received = received

class AuthenticationError(FunctionCallError):
    """Raised when authentication or authorization fails."""
    def __init__(self, message: str = None):
        if message is None:
            message = "Authentication or authorization failed during function execution."
        super().__init__(message)

class PermissionDeniedError(FunctionCallError):
    """Raised when the operation cannot be performed due to insufficient permissions."""
    def __init__(self, message: str = None):
        if message is None:
            message = "Permission denied: insufficient privileges to perform the requested operation."
        super().__init__(message)


class RateLimitError(FunctionCallError):
    """Raised when API rate limits or quotas are exceeded."""
    def __init__(self, message: str = None):
        if message is None:
            message = "API rate limit exceeded or quota reached."
        super().__init__(message)


class HTTPError(FunctionCallError):
    """Raised for HTTP errors such as 4xx or 5xx status codes."""
    def __init__(self, status_code: int = None, message: str = None):
        if message is None:
            if status_code is not None:
                message = f"HTTP error occurred with status code {status_code}."
            else:
                message = "An HTTP error occurred."
        super().__init__(message)
        self.status_code = status_code


class APISpecificError(FunctionCallError):
    """Raised for service-specific error responses from an API."""
    def __init__(self, error_code: int = None, message: str = None):
        if message is None:
            if error_code is not None:
                message = f"API-specific error occurred with error code {error_code}."
            else:
                message = "An API-specific error occurred."
        super().__init__(message)
        self.error_code = error_code

class TimeoutError(FunctionCallError):
    """Raised when a function or tool call times out."""
    def __init__(self, timeout: float = None, message: str = None):
        if message is None:
            if timeout is not None:
                message = f"Function call timed out after {timeout} seconds."
            else:
                message = "Function call timed out."
        super().__init__(message)
        self.timeout = timeout

class ErrorHandlingFailure(FunctionCallError):
    """Raised when the error handling mechanism itself fails."""
    def __init__(self, message: str = None):
        if message is None:
            message = "The error handling mechanism itself failed."
        super().__init__(message)
