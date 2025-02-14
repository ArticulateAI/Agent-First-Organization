# Base Exception
class FunctionCallError(Exception):
    """Base exception for all errors related to LLM function or tool calls."""
    def __init__(self, message: str = None):
        if message is None:
            message = "An error occurred during an LLM function or tool call."
        super().__init__(message)



class OutputError(FunctionCallError):
    """General error for issues in LLM-generated output."""
    def __init__(self, message: str = None):
        if message is None:
            message = "There was an error with the LLM output."
        super().__init__(message)


class ParameterMissingError(OutputError):
    """Raised when there is a missing parameter."""
    def __init__(self, parameter: str, message: str = None):
        if message is None:
            message = f"The required parameter '{parameter}' is missing."
        super().__init__(message)
        self.parameter = parameter


class ParameterMismatchError(OutputError):
    """Raised when the parameters provided do not match the expected schema or types."""
    def __init__(self, parameter: str, expected: str, received: str, message: str = None):
        if message is None:
            message = (f"Parameter '{parameter}' mismatch: expected type/schema '{expected}', "
                       f"but received '{received}'.")
        super().__init__(message)
        self.parameter = parameter
        self.expected = expected
        self.received = received




class RuntimeFunctionError(FunctionCallError):
    """General error for issues encountered during function/tool execution."""
    def __init__(self, message: str = None):
        if message is None:
            message = "An error occurred during the execution of a function or tool."
        super().__init__(message)


class InternalFunctionError(RuntimeFunctionError):
    """Raised for internal errors like runtime exceptions or logic errors within the function."""
    def __init__(self, message: str = None):
        if message is None:
            message = "An internal error occurred during function execution."
        super().__init__(message)


class NetworkError(RuntimeFunctionError):
    """Raised for network-related issues (timeouts, connection failures, etc.)."""
    def __init__(self, message: str = None):
        if message is None:
            message = "A network error occurred during function execution."
        super().__init__(message)


class AuthenticationError(RuntimeFunctionError):
    """Raised when authentication or authorization fails."""
    def __init__(self, message: str = None):
        if message is None:
            message = "Authentication or authorization failed during function execution."
        super().__init__(message)


class RateLimitError(RuntimeFunctionError):
    """Raised when API rate limits or quotas are exceeded."""
    def __init__(self, message: str = None):
        if message is None:
            message = "API rate limit exceeded or quota reached."
        super().__init__(message)


class HTTPError(RuntimeFunctionError):
    """Raised for HTTP errors such as 4xx or 5xx status codes."""
    def __init__(self, status_code: int = None, message: str = None):
        if message is None:
            if status_code is not None:
                message = f"HTTP error occurred with status code {status_code}."
            else:
                message = "An HTTP error occurred."
        super().__init__(message)
        self.status_code = status_code


class APISpecificError(RuntimeFunctionError):
    """Raised for service-specific error responses from an API."""
    def __init__(self, error_code: int = None, message: str = None):
        if message is None:
            if error_code is not None:
                message = f"API-specific error occurred with error code {error_code}."
            else:
                message = "An API-specific error occurred."
        super().__init__(message)
        self.error_code = error_code


class DependencyError(RuntimeFunctionError):
    """Raised when a required external dependency or library is missing."""
    def __init__(self, dependency: str, message: str = None):
        if message is None:
            message = f"The required dependency '{dependency}' is missing."
        super().__init__(message)
        self.dependency = dependency


class TimeoutError(RuntimeFunctionError):
    """Raised when a function or tool call times out."""
    def __init__(self, timeout: float = None, message: str = None):
        if message is None:
            if timeout is not None:
                message = f"Function call timed out after {timeout} seconds."
            else:
                message = "Function call timed out."
        super().__init__(message)
        self.timeout = timeout


class HangingCallError(RuntimeFunctionError):
    """Raised when a function/tool call hangs indefinitely without a response."""
    def __init__(self, message: str = None):
        if message is None:
            message = "Function call appears to be hanging without a response."
        super().__init__(message)




class UnforeseenException(FunctionCallError):
    """Raised for unforeseen or unexpected exceptions not covered by other error types."""
    def __init__(self, original_exception: Exception, message: str = None):
        if message is None:
            message = f"An unforeseen exception occurred: {original_exception}"
        super().__init__(message)
        self.original_exception = original_exception


class ErrorHandlingFailure(FunctionCallError):
    """Raised when the error handling mechanism itself fails."""
    def __init__(self, message: str = None):
        if message is None:
            message = "The error handling mechanism itself failed."
        super().__init__(message)
