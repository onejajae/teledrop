from typing import Annotated

from fastapi import Depends, Request, Response

from app.application.auth.models import VerifySessionQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import (
    PasswordLoginUseCase,
    RevokeSessionUseCase,
    VerifySessionUseCase,
)
from app.bootstrap.container import AuthUseCasesDep, SettingsDep
from app.core.auth import clear_session_cookie, get_session_id_from_request
from app.domain.auth.errors import SessionExpired, SessionInvalid
from app.interfaces.api.errors import (
    response_set_cookie_header,
    session_unauthorized_exception,
)


def get_verify_session_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> VerifySessionUseCase:
    return auth_use_cases.verify_session_use_case


def get_revoke_session_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> RevokeSessionUseCase:
    return auth_use_cases.revoke_session_use_case


def get_password_login_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> PasswordLoginUseCase:
    return auth_use_cases.password_login_use_case


class Authenticator:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(
        self,
        request: Request,
        response: Response,
        settings: SettingsDep,
        verify_session_use_case: VerifySessionUseCase = Depends(get_verify_session_use_case),
    ) -> AuthIdentity:
        session_id = get_session_id_from_request(request, settings)
        if session_id:
            try:
                username = await verify_session_use_case.execute(VerifySessionQuery(sid=session_id))
            except (SessionExpired, SessionInvalid):
                clear_session_cookie(response, settings)
                if self.auto_error:
                    raise session_unauthorized_exception(
                        detail="Invalid or expired session.",
                        set_cookie=response_set_cookie_header(response),
                    )
                return AuthIdentity(username=None)

            return AuthIdentity(username=username)

        if self.auto_error:
            clear_session_cookie(response, settings)
            raise session_unauthorized_exception(
                detail="Authentication credentials were not provided or are invalid.",
                set_cookie=response_set_cookie_header(response),
            )

        return AuthIdentity(username=None)


AuthDep = Annotated[AuthIdentity, Depends(Authenticator())]
RequiredAuthDep = Annotated[AuthIdentity, Depends(Authenticator(auto_error=True))]
OptionalAuthDep = Annotated[AuthIdentity, Depends(Authenticator(auto_error=False))]
PasswordLoginUseCaseDep = Annotated[PasswordLoginUseCase, Depends(get_password_login_use_case)]
RevokeSessionUseCaseDep = Annotated[RevokeSessionUseCase, Depends(get_revoke_session_use_case)]


__all__ = [
    "AuthDep",
    "Authenticator",
    "OptionalAuthDep",
    "PasswordLoginUseCaseDep",
    "RequiredAuthDep",
    "RevokeSessionUseCaseDep",
    "get_password_login_use_case",
    "get_revoke_session_use_case",
    "get_verify_session_use_case",
]
