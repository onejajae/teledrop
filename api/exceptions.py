# Content
class ContentNotExist(Exception):
    pass


class ContentNeedLogin(Exception):
    pass


class ContentPasswordInvalid(Exception):
    pass


# Auth
class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass
