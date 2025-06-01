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


class PermissionDeniedError(TeledropError):
    """Permission related errors"""
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


# File related exceptions
class DropFileNotFoundError(NotFoundError):
    """File not found error"""
    pass


class FileSizeExceededError(ValidationError):
    """File size exceeded error"""
    pass


class FileUploadError(TeledropError):
    """File upload error"""
    pass


# API Key related exceptions
class ApiKeyInvalidError(ValidationError):
    """API Key invalid error"""
    pass


class ApiKeyExpiredError(ValidationError):
    """API Key expired error"""
    pass


class ApiKeyNotFoundError(NotFoundError):
    """API Key not found error"""
    pass


# Authentication related exceptions
class AuthenticationError(TeledropError):
    """Authentication related errors"""
    pass


class TokenExpiredError(AuthenticationError):
    """Token expired error"""
    pass


class TokenInvalidError(AuthenticationError):
    """Token invalid error"""
    pass


class LoginInvalidError(AuthenticationError):
    """Login invalid error"""
    pass


# Storage related exceptions
class StorageError(TeledropError):
    """Storage related errors"""
    pass


class StorageNotFoundError(StorageError):
    """Storage file not found error"""
    pass


class StorageAccessError(StorageError):
    """Storage access error"""
    pass


class DropKeyAlreadyExistsError(Exception):
    """Drop key가 이미 존재할 때 발생하는 예외"""
    pass 