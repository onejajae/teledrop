import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlmodel import Session, select

from app.application.auth.ports import AuthApiKeyCreateInput
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.db.models.user import UserRecord as DbUserRecord
from app.infrastructure.db.repositories.api_key_repository import (
    SQLModelApiKeyMutationRepository,
    SQLModelApiKeyReadRepository,
)
from tests.support.alembic import upgrade_sqlite_db


class TestApiKeyRepository:
    def setup_method(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "api-keys.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        upgrade_sqlite_db(sqlite_url)
        settings = SimpleNamespace(SQLITE_HOST=sqlite_url)
        self.engine = create_db_engine(settings)
        self.session_factory = create_db_session_factory(self.engine)
        self.read_repository = SQLModelApiKeyReadRepository(self.session_factory)
        self.owner_user_id = self._get_bootstrap_user_id()
        self.other_user_id = self._create_user("another-user")

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

    async def test_create_get_touch_revoke_delete_flow(self):
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            repository = SQLModelApiKeyMutationRepository(session)
            created = await repository.create(
                AuthApiKeyCreateInput(
                    public_id="pub1",
                    name="shortcuts",
                    owner_user_id=self.owner_user_id,
                    key_hash="hash-1",
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                )
            )
            await repository.touch_last_used_at("pub1", used_at=now + timedelta(minutes=1))
            await repository.revoke_by_public_id(
                "pub1",
                owner_user_id=self.owner_user_id,
                revoked_at=now + timedelta(minutes=2),
            )
            session.commit()

        assert created.public_id == "pub1"
        assert created.owner_user_id == self.owner_user_id

        fetched = await self.read_repository.get_by_public_id("pub1")
        assert fetched is not None
        assert fetched.name == "shortcuts"
        assert fetched.owner_user_id == self.owner_user_id
        assert fetched.last_used_at is not None
        assert fetched.revoked_at is not None

        listed = await self.read_repository.list_for_owner(self.owner_user_id)
        assert len(listed) == 1
        assert listed[0].public_id == "pub1"

        with self.session_factory() as session:
            repository = SQLModelApiKeyMutationRepository(session)
            deleted = await repository.delete_by_public_id(
                "pub1",
                owner_user_id=self.owner_user_id,
            )
            session.commit()

        assert deleted
        assert await self.read_repository.get_by_public_id("pub1") is None

    async def test_owner_scoped_queries_and_mutations_ignore_other_users(self):
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            repository = SQLModelApiKeyMutationRepository(session)
            await repository.create(
                AuthApiKeyCreateInput(
                    public_id="owner-key",
                    name="owner",
                    owner_user_id=self.owner_user_id,
                    key_hash="hash-owner",
                    created_at=now,
                    expires_at=None,
                )
            )
            await repository.create(
                AuthApiKeyCreateInput(
                    public_id="other-key",
                    name="other",
                    owner_user_id=self.other_user_id,
                    key_hash="hash-other",
                    created_at=now + timedelta(seconds=1),
                    expires_at=None,
                )
            )
            session.commit()

        listed = await self.read_repository.list_for_owner(self.owner_user_id)
        assert [item.public_id for item in listed] == ["owner-key"]

        with self.session_factory() as session:
            repository = SQLModelApiKeyMutationRepository(session)
            revoked = await repository.revoke_by_public_id(
                "other-key",
                owner_user_id=self.owner_user_id,
                revoked_at=now + timedelta(minutes=1),
            )
            deleted = await repository.delete_by_public_id(
                "other-key",
                owner_user_id=self.owner_user_id,
            )
            session.commit()

        assert revoked is None
        assert not deleted
        assert await self.read_repository.get_by_public_id("other-key") is not None
