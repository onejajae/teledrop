"""Core exceptions for Teledrop application

새로운 아키텍처에서 사용되는 예외 클래스들을 정의합니다.
Handler 레이어에서 발생하는 비즈니스 로직 예외들을 포함합니다.
"""


# Base exceptions
class TeledropError(Exception):
    """Base exception for all Teledrop errors"""
    pass


class ValidationError(TeledropError):
    """Validation related errors"""
    pass


class NotFoundError(TeledropError):
    """Resource not found errors"""
    pass


class AccessDeniedError(TeledropError):
    """Access denied errors"""
    pass


# Drop related exceptions
class DropNotFoundError(NotFoundError):
    """Drop not found error"""
    pass


class DropPasswordInvalidError(ValidationError):
    """Drop password invalid error"""
    pass


class DropAccessDeniedError(AccessDeniedError):
    """Drop access denied error"""
    pass


class DropSlugAlreadyExistsError(ValidationError):
    """Drop slug가 이미 존재할 때 발생하는 예외"""
    pass


# Range related exceptions
class InvalidRangeHeaderError(ValidationError):
    """Range header format is invalid"""
    pass


class RangeNotSatisfiableError(ValidationError):
    """Requested range cannot be satisfied"""
    pass


# Authentication related exceptions
class AuthenticationError(TeledropError):
    """Authentication related errors"""
    pass


class AuthenticationRequiredError(AuthenticationError):
    """인증이 필요할 때 발생하는 예외"""
    pass


# Storage related exceptions
class StorageError(TeledropError):
    """Storage related errors"""
    pass
