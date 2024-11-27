class PostNotExist(Exception):
    pass


class PostNeedLogin(Exception):
    pass


class UserNotHavePostPermission(Exception):
    pass


class PostPasswordInvalid(Exception):
    pass
