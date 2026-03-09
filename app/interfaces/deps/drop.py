from typing import Annotated

from fastapi import Depends

from app.application.drop.use_cases import (
    CheckSlugAvailabilityUseCase,
    CreateDropUseCase,
    DeleteDropUseCase,
    GetDropMetaUseCase,
    GetDropStreamSourceUseCase,
    ListDropsUseCase,
    UpdateDropUseCase,
)
from app.bootstrap.container import AppContainerDep


def get_create_drop_use_case(container: AppContainerDep) -> CreateDropUseCase:
    return container.create_drop_use_case


def get_list_drops_use_case(container: AppContainerDep) -> ListDropsUseCase:
    return container.list_drops_use_case


def get_get_drop_meta_use_case(container: AppContainerDep) -> GetDropMetaUseCase:
    return container.get_drop_meta_use_case


def get_get_drop_stream_source_use_case(
    container: AppContainerDep,
) -> GetDropStreamSourceUseCase:
    return container.get_drop_stream_source_use_case


def get_update_drop_use_case(container: AppContainerDep) -> UpdateDropUseCase:
    return container.update_drop_use_case


def get_delete_drop_use_case(container: AppContainerDep) -> DeleteDropUseCase:
    return container.delete_drop_use_case


def get_check_slug_availability_use_case(
    container: AppContainerDep,
) -> CheckSlugAvailabilityUseCase:
    return container.check_slug_availability_use_case


CreateDropUseCaseDep = Annotated[CreateDropUseCase, Depends(get_create_drop_use_case)]
ListDropsUseCaseDep = Annotated[ListDropsUseCase, Depends(get_list_drops_use_case)]
GetDropMetaUseCaseDep = Annotated[GetDropMetaUseCase, Depends(get_get_drop_meta_use_case)]
GetDropStreamSourceUseCaseDep = Annotated[
    GetDropStreamSourceUseCase,
    Depends(get_get_drop_stream_source_use_case),
]
UpdateDropUseCaseDep = Annotated[UpdateDropUseCase, Depends(get_update_drop_use_case)]
DeleteDropUseCaseDep = Annotated[DeleteDropUseCase, Depends(get_delete_drop_use_case)]
CheckSlugAvailabilityUseCaseDep = Annotated[
    CheckSlugAvailabilityUseCase,
    Depends(get_check_slug_availability_use_case),
]


__all__ = [
    "CheckSlugAvailabilityUseCaseDep",
    "CreateDropUseCaseDep",
    "DeleteDropUseCaseDep",
    "GetDropMetaUseCaseDep",
    "GetDropStreamSourceUseCaseDep",
    "ListDropsUseCaseDep",
    "UpdateDropUseCaseDep",
    "get_check_slug_availability_use_case",
    "get_create_drop_use_case",
    "get_delete_drop_use_case",
    "get_get_drop_meta_use_case",
    "get_get_drop_stream_source_use_case",
    "get_list_drops_use_case",
    "get_update_drop_use_case",
]
