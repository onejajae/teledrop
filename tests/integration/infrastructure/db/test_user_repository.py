import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.application.auth.ports import UserCreateInput
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.db.models.user import UserRecord as DbUserRecord
from app.infrastructure.db.repositories.user_repository import SQLModelUserReadRepository
from app.infrastructure.db.uow_user import SQLModelUserUnitOfWork
from tests.support.db import initialize_sqlite_db


class TestUserRepository:
    def setup_method(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "users.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        initialize_sqlite_db(sqlite_url)
        settings = SimpleNamespace(SQLITE_HOST=sqlite_url)
        self.engine = create_db_engine(settings)
        self.session_factory = create_db_session_factory(self.engine)
        self.repository = SQLModelUserReadRepository(self.session_factory)

    def teardown_method(self):
        self.engine.dispose()
        self._temp_dir.cleanup()

    async def test_get_by_id_and_username_returns_bootstrapped_user(self):
        with self.session_factory() as session:
            user = session.exec(
                select(DbUserRecord).where(DbUserRecord.username == "admin")
            ).one()

        by_username = await self.repository.get_by_username("admin")
        by_id = await self.repository.get_by_id(user.id.hex)

        assert by_username is not None
        assert by_id is not None
        assert by_username.id == user.id.hex
        assert by_id.username == "admin"

    async def test_user_unit_of_work_creates_user(self):
        now = datetime.now(timezone.utc)

        async with SQLModelUserUnitOfWork(self.session_factory) as uow:
            created = await uow.repository.create(
                UserCreateInput(
                    username="tester",
                    password_hash="hash",
                    created_at=now,
                    updated_at=now,
                    disabled_at=None,
                )
            )
            await uow.commit()

        by_username = await self.repository.get_by_username("tester")

        assert by_username is not None
        assert by_username.id == created.id
        assert by_username.password_hash == "hash"

    async def test_user_unit_of_work_rejects_duplicate_username(self):
        now = datetime.now(timezone.utc)

        with pytest.raises(IntegrityError):
            async with SQLModelUserUnitOfWork(self.session_factory) as uow:
                await uow.repository.create(
                    UserCreateInput(
                        username="admin",
                        password_hash="hash",
                        created_at=now,
                        updated_at=now,
                        disabled_at=None,
                    )
                )
