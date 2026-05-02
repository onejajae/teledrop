class LoginInvalid(Exception):
    pass


class RegistrationDisabled(Exception):
    pass


class RegistrationInvalid(Exception):
    pass


class UsernameInvalid(RegistrationInvalid):
    pass


class PasswordTooShort(RegistrationInvalid):
    pass


class PasswordConfirmationMismatch(RegistrationInvalid):
    pass


class UsernameUnavailable(RegistrationInvalid):
    pass


class SessionExpired(Exception):
    pass


class SessionInvalid(Exception):
    pass


class ApiKeyInvalid(Exception):
    pass


class ApiKeyNotFound(Exception):
    pass
