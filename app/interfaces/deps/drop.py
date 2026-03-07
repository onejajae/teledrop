from typing import Annotated

from fastapi import Depends

from app.bootstrap.container import (
    AppContainerDep,
    DropUseCaseCollection,
)


def get_drop_use_cases(container: AppContainerDep) -> DropUseCaseCollection:
    return container.drop_use_cases


DropUseCasesDep = Annotated[DropUseCaseCollection, Depends(get_drop_use_cases)]


__all__ = [
    "DropUseCasesDep",
    "get_drop_use_cases",
]
