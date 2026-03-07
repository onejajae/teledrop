from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy.engine import Engine

from app.bootstrap.runtime_paths import project_root_dir


ALEMBIC_UPGRADE_COMMAND = "uv run alembic -c alembic.ini upgrade head"


class DatabaseSchemaOutOfDateError(RuntimeError):
    pass


def _build_alembic_config() -> Config:
    root_dir = project_root_dir()
    config = Config(str(root_dir / "alembic.ini"))
    config.set_main_option("script_location", str(root_dir / "migrations"))
    return config


def _expected_heads(script: ScriptDirectory) -> tuple[str, ...]:
    heads = tuple(script.get_heads())
    if len(heads) != 1:
        raise RuntimeError("Expected a single Alembic head revision.")
    return heads


def _upgrade_hint(reason: str) -> str:
    return f"{reason} Run `{ALEMBIC_UPGRADE_COMMAND}`."


def assert_db_schema_current(db_engine: Engine) -> None:
    script = ScriptDirectory.from_config(_build_alembic_config())
    expected_heads = _expected_heads(script)

    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_heads = tuple(context.get_current_heads())

    if not current_heads:
        raise DatabaseSchemaOutOfDateError(
            _upgrade_hint("Database schema is not initialized or has no recorded Alembic revision.")
        )

    for revision in current_heads:
        try:
            resolved = script.get_revision(revision)
        except CommandError as exc:
            raise DatabaseSchemaOutOfDateError(
                _upgrade_hint(
                    f"Database schema revision '{revision}' is not recognized by this codebase."
                )
            ) from exc

        if resolved is None:
            raise DatabaseSchemaOutOfDateError(
                _upgrade_hint(
                    f"Database schema revision '{revision}' is not recognized by this codebase."
                )
            )

    if set(current_heads) != set(expected_heads):
        current_display = ", ".join(current_heads)
        expected_display = ", ".join(expected_heads)
        raise DatabaseSchemaOutOfDateError(
            _upgrade_hint(
                f"Database schema revision '{current_display}' is not current; "
                f"expected '{expected_display}'."
            )
        )


__all__ = [
    "ALEMBIC_UPGRADE_COMMAND",
    "DatabaseSchemaOutOfDateError",
    "assert_db_schema_current",
]
