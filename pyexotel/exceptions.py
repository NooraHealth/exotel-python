class PyexotelBaseException(Exception):
    pass


class AuthenticationFailed(PyexotelBaseException):
    pass


class PermissionDenied(PyexotelBaseException):
    pass


class PaymentRequired(PyexotelBaseException):
    pass


class Throttled(PyexotelBaseException):
    pass


class UniqueViolationError(PyexotelBaseException):
    pass
