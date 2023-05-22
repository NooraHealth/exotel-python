class PyexotelBaseException(Exception):
    pass


class ValidationError(PyexotelBaseException):
    """
        Raised when 400 status code is returned by Exotel API
    """
    pass


class AuthenticationFailed(PyexotelBaseException):
    """
        Raised when 401 status code is returned by Exotel API
    """
    pass


class PaymentRequired(PyexotelBaseException):
    """
        Raised when 402 status code is returned by Exotel API
    """
    pass


class NotFound(PyexotelBaseException):
    """
        Raised when 404 status code is returned by Exotel API
    """
    pass


class PermissionDenied(PyexotelBaseException):
    """
        Raised when 403 status code is returned by Exotel API
    """
    pass


class Throttled(PyexotelBaseException):
    """
        Raised when 429 status code is returned by Exotel API
    """
    pass


class UniqueViolationError(PyexotelBaseException):
    pass
