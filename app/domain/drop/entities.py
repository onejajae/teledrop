from dataclasses import dataclass
from datetime import datetime

from app.domain.drop.value_objects import AccessScope


@dataclass(slots=True)
class DropEntity:
    id: str
    owner_user_id: str
    slug: str
    access_scope: AccessScope
    is_favorite: bool
    drop_password: str | None
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_key: str
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    @property
    def requires_password(self) -> bool:
        return bool(self.drop_password)
