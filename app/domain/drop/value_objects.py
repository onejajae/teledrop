from enum import Enum


class AccessScope(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class DropSortField(str, Enum):
    CREATED_AT = "created_at"
    TITLE = "title"
    SIZE_BYTES = "size_bytes"
