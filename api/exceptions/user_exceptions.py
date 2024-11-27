class RegisterNotAllowedError(Exception):
    pass


class RegisterCodeNotMatchedError(Exception):
    pass


class DuplicateUserError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class PasswordInvlaidError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass
