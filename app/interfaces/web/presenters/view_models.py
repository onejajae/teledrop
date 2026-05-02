from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


DisplayDate = datetime | str | None
DetailMode = Literal["panel", "manage", "shared"]


@dataclass(slots=True, frozen=True)
class SortOptionVM:
    value: str
    label: str


@dataclass(slots=True, frozen=True)
class DropVM:
    owner_user_id: str
    slug: str
    title: str | None
    description: str | None
    file_name: str
    mime_type: str
    size_bytes: int
    access_scope: str
    is_favorite: bool
    requires_password: bool
    created_at: DisplayDate
    updated_at: DisplayDate
    size_human: str | None
    created_at_label: str | None
    updated_at_label: str | None
    created_at_relative: str | None


@dataclass(slots=True, frozen=True)
class DetailErrorVM:
    message: str | None = None
    code: str | None = None


@dataclass(slots=True, frozen=True)
class DetailUrlsVM:
    download: str | None = None
    page: str | None = None
    manage: str | None = None


@dataclass(slots=True, frozen=True)
class DetailBadgeVM:
    label: str | None = None
    tone: str | None = None
    appearance: str | None = None


@dataclass(slots=True, frozen=True)
class DetailActionsVM:
    can_copy_link: bool = True
    show_owner_actions: bool = False
    show_shared_admin_bar: bool = False
    password_clear_enabled: bool = False


@dataclass(slots=True, frozen=True)
class DetailFormsVM:
    locked_prompt_action: str | None = None
    unlock_target_view: DetailMode = "shared"
    unlock_token: str | None = None


@dataclass(slots=True, frozen=True)
class DetailVM:
    slug: str | None = None
    mode: DetailMode = "panel"
    drop: DropVM | None = None
    requires_password: bool = False
    access_granted: bool = False
    invalid_grant: bool = False
    status_message: str | None = None
    error: DetailErrorVM = field(default_factory=DetailErrorVM)
    urls: DetailUrlsVM = field(default_factory=DetailUrlsVM)
    badge: DetailBadgeVM = field(default_factory=DetailBadgeVM)
    actions: DetailActionsVM = field(default_factory=DetailActionsVM)
    forms: DetailFormsVM = field(default_factory=DetailFormsVM)


@dataclass(slots=True, frozen=True)
class ApiKeyVM:
    public_id: str
    name: str
    created_at: DisplayDate
    expires_at: DisplayDate
    last_used_at: DisplayDate
    revoked_at: DisplayDate
    is_active: bool


@dataclass(slots=True, frozen=True)
class CreatedApiKeyVM:
    key: str


__all__ = [
    "ApiKeyVM",
    "CreatedApiKeyVM",
    "DetailActionsVM",
    "DetailBadgeVM",
    "DetailErrorVM",
    "DetailFormsVM",
    "DetailMode",
    "DetailUrlsVM",
    "DetailVM",
    "DisplayDate",
    "DropVM",
    "SortOptionVM",
]
