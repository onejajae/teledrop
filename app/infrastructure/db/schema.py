from datetime import datetime, timezone

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func
from sqlmodel import SQLModel, Session, select
from argon2 import PasswordHasher, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.infrastructure.db.models import AuthApiKey, AuthSession, DropRecord, UserRecord


INCOMPATIBLE_DATABASE_HINT = (
    "Existing database schema is not compatible with this version. "
    "Back up and remove the old database file, then restart teledrop to create a fresh database."
)

_CURRENT_REQUIRED_COLUMNS = {
    "users": {"id", "username", "password_hash", "created_at", "updated_at", "disabled_at"},
    "drops": {
        "id",
        "owner_user_id",
        "slug",
        "access_scope",
        "is_favorite",
        "drop_password",
        "file_name",
        "mime_type",
        "size_bytes",
        "sha256",
        "storage_key",
        "title",
        "description",
        "created_at",
        "updated_at",
    },
    "auth_sessions": {"sid", "user_id", "created_at", "expires_at", "revoked_at"},
    "auth_api_keys": {
        "id",
        "public_id",
        "name",
        "owner_user_id",
        "key_hash",
        "created_at",
        "expires_at",
        "last_used_at",
        "revoked_at",
    },
}
_LEGACY_TABLES = {"alembic_version", "content", "contents"}


class DatabaseSchemaIncompatibleError(RuntimeError):
    pass


class BootstrapConfigurationError(RuntimeError):
    pass


def initialize_database_schema(db_engine: Engine, settings: Settings) -> None:
    _assert_database_compatible(db_engine)
    SQLModel.metadata.create_all(db_engine)
    _bootstrap_initial_user(db_engine, settings)


def _assert_database_compatible(db_engine: Engine) -> None:
    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())

    legacy_tables = table_names & _LEGACY_TABLES
    if legacy_tables:
        _raise_incompatible(f"legacy table(s) found: {', '.join(sorted(legacy_tables))}")

    for table_name, required_columns in _CURRENT_REQUIRED_COLUMNS.items():
        if table_name not in table_names:
            continue
        current_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = required_columns - current_columns
        if missing_columns:
            _raise_incompatible(
                f"table '{table_name}' is missing column(s): {', '.join(sorted(missing_columns))}"
            )


def _bootstrap_initial_user(db_engine: Engine, settings: Settings) -> None:
    now = datetime.now(timezone.utc)
    with Session(db_engine) as session:
        user_count = session.exec(select(func.count()).select_from(UserRecord)).one()
        if int(user_count) > 0:
            return

        _validate_bootstrap_credentials(settings)

        session.add(
            UserRecord(
                username=settings.WEB_USERNAME,
                password_hash=settings.WEB_PASSWORD,
                created_at=now,
                updated_at=now,
                disabled_at=None,
            )
        )
        session.commit()


def _validate_bootstrap_credentials(settings: Settings) -> None:
    username = (settings.WEB_USERNAME or "").strip()
    password_hash = (settings.WEB_PASSWORD or "").strip()
    if not username or not password_hash:
        raise BootstrapConfigurationError(
            "WEB_USERNAME and WEB_PASSWORD must be set before bootstrapping "
            "the initial user."
        )

    if not _is_argon2_password_hash(password_hash):
        raise BootstrapConfigurationError(
            "WEB_PASSWORD must be a valid Argon2 password hash before "
            "bootstrapping the initial user."
        )

    if _uses_insecure_bootstrap_defaults(settings, username, password_hash):
        raise BootstrapConfigurationError(
            "Refusing to bootstrap the default admin/password user while "
            "BOOTSTRAP_ALLOW_INSECURE_DEFAULTS is false."
        )


def _is_argon2_password_hash(password_hash: str) -> bool:
    try:
        extract_parameters(password_hash)
    except InvalidHashError:
        return False
    return True


def _uses_insecure_bootstrap_defaults(
    settings: Settings,
    username: str,
    password_hash: str,
) -> bool:
    if getattr(settings, "BOOTSTRAP_ALLOW_INSECURE_DEFAULTS", True):
        return False
    if username != "admin":
        return False
    try:
        return PasswordHasher().verify(password_hash, "password")
    except (InvalidHashError, VerificationError):
        return False


def _raise_incompatible(reason: str) -> None:
    raise DatabaseSchemaIncompatibleError(f"{reason}. {INCOMPATIBLE_DATABASE_HINT}")


__all__ = [
    "DatabaseSchemaIncompatibleError",
    "BootstrapConfigurationError",
    "INCOMPATIBLE_DATABASE_HINT",
    "initialize_database_schema",
]
