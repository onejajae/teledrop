from typing import Annotated

from fastapi import Depends

from app.application.auth.use_cases import CsrfTokenService
from app.bootstrap.container import AppContainerDep


def get_csrf_token_service(
    container: AppContainerDep,
) -> CsrfTokenService:
    return container.csrf_token_service


CsrfTokenServiceDep = Annotated[CsrfTokenService, Depends(get_csrf_token_service)]


__all__ = [
    "CsrfTokenServiceDep",
    "get_csrf_token_service",
]
