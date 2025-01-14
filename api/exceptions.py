# Content
class ContentNotExist(Exception):
    pass


class ContentNeedLogin(Exception):
    pass


class ContentPasswordInvalid(Exception):
    pass


# Auth
class LoginInvalid(Exception):
    pass


class TokenExpired(Exception):
    pass


class TokenInvalid(Exception):
    pass
