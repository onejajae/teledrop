import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlmodel import select

from app.application.drop.ports import DropCreateInput, DropUpdateInput
from app.domain.drop.value_objects import AccessScope, DropSortField
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.db.models.user import UserRecord as DbUserRecord
from app.infrastructure.db.repositories import SQLModelDropReadRepository
from app.infrastructure.db.uow_drop import SQLModelDropUnitOfWork
from tests.support.alembic import upgrade_sqlite_db


def _drop_create_input(slug: str, owner_user_id: str) -> DropCreateInput:
    return DropCreateInput(
        owner_user_id=owner_user_id,
        slug=slug,
        access_scope=AccessScope.PRIVATE,
        is_favorite=False,
        drop_password=None,
        file_name=f"{slug}.txt",
        mime_type="text/plain",
        size_bytes=3,
        sha256=f"sha-{slug}",
        storage_key=f"storage-{slug}",
        title=slug,
        description=None,
    )


class TestDropUnitOfWork:
    def setup_method(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "uow.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        upgrade_sqlite_db(sqlite_url)
        settings = SimpleNamespace(SQLITE_HOST=sqlite_url)
        self.engine = create_db_engine(settings)
        self.session_factory = create_db_session_factory(self.engine)
        self.read_repository = SQLModelDropReadRepository(self.session_factory)
        self.owner_user_id = self._get_bootstrap_user_id()
        self.other_user_id = self._create_user("other-owner")

    def teardown_method(self):
        self.engine.dispose()
        self._temp_dir.cleanup()

    def _get_bootstrap_user_id(self) -> str:
        with self.session_factory() as session:
            user = session.exec(
                select(DbUserRecord).where(DbUserRecord.username == "admin")
            ).one()
            return user.id.hex

    def _create_user(self, username: str) -> str:
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            user = DbUserRecord(
                username=username,
                password_hash=f"hash-{username}",
                created_at=now,
                updated_at=now,
                disabled_at=None,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user.id.hex

    async def test_drop_uow_commit_persists_writes(self):
        async with SQLModelDropUnitOfWork(self.session_factory) as uow:
            await uow.repository.create(_drop_create_input("commit-slug", self.owner_user_id))
            await uow.commit()

        persisted = await self.read_repository.get_by_slug("commit-slug")
        assert persisted is not None
        assert persisted.owner_user_id == self.owner_user_id

    async def test_drop_uow_rolls_back_when_exception_occurs(self):
        with pytest.raises(RuntimeError):
            async with SQLModelDropUnitOfWork(self.session_factory) as uow:
                await uow.repository.create(
                    _drop_create_input("rollback-slug", self.owner_user_id)
                )
                raise RuntimeError("force rollback")

        persisted = await self.read_repository.get_by_slug("rollback-slug")
        assert persisted is None

    async def test_drop_uow_repository_requires_active_session(self):
        uow = SQLModelDropUnitOfWork(self.session_factory)

        with pytest.raises(RuntimeError, match="not active"):
            _ = uow.repository

        async with uow:
            _ = uow.repository

        with pytest.raises(RuntimeError, match="not active"):
            _ = uow.repository

    async def test_captured_drop_repository_rejects_writes_after_uow_exit(self):
        async with SQLModelDropUnitOfWork(self.session_factory) as uow:
            repository = uow.repository

        with pytest.raises(RuntimeError, match="not active"):
            await repository.create(_drop_create_input("leaked-slug", self.owner_user_id))

        persisted = await self.read_repository.get_by_slug("leaked-slug")
        assert persisted is None

    async def test_drop_read_repository_scopes_list_count_and_owned_lookup(self):
        async with SQLModelDropUnitOfWork(self.session_factory) as uow:
            await uow.repository.create(_drop_create_input("owner-drop", self.owner_user_id))
            await uow.repository.create(_drop_create_input("other-drop", self.other_user_id))
            await uow.commit()

        listed = await self.read_repository.list(
            owner_user_id=self.owner_user_id,
            limit=10,
            offset=0,
            sort=DropSortField.CREATED_AT,
            order="desc",
        )
        total = await self.read_repository.count(owner_user_id=self.owner_user_id)
        owned = await self.read_repository.get_owned_by_slug(
            "owner-drop",
            owner_user_id=self.owner_user_id,
        )
        not_owned = await self.read_repository.get_owned_by_slug(
            "other-drop",
            owner_user_id=self.owner_user_id,
        )

        assert [item.slug for item in listed] == ["owner-drop"]
        assert total == 1
        assert owned is not None
        assert not_owned is None

    async def test_drop_mutations_require_matching_owner(self):
        async with SQLModelDropUnitOfWork(self.session_factory) as uow:
            await uow.repository.create(_drop_create_input("owned-drop", self.owner_user_id))
            await uow.commit()

        async with SQLModelDropUnitOfWork(self.session_factory) as uow:
            updated = await uow.repository.update_by_slug(
                "owned-drop",
                owner_user_id=self.other_user_id,
                data=DropUpdateInput(title="wrong-owner"),
            )
            deleted = await uow.repository.delete_by_slug(
                "owned-drop",
                owner_user_id=self.other_user_id,
            )
            await uow.commit()

        persisted = await self.read_repository.get_by_slug("owned-drop")
        assert updated is None
        assert not deleted
        assert persisted is not None
        assert persisted.title == "owned-drop"
