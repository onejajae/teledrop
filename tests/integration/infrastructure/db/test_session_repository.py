import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlmodel import select

from app.application.auth.ports import AuthSessionCreateInput
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.db.models.user import UserRecord as DbUserRecord
from app.infrastructure.db.repositories.session_repository import (
    SQLModelSessionMutationRepository,
    SQLModelSessionReadRepository,
)
from tests.support.alembic import upgrade_sqlite_db


class TestSessionRepository:
    def setup_method(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "sessions.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        upgrade_sqlite_db(sqlite_url)
        settings = SimpleNamespace(SQLITE_HOST=sqlite_url)
        self.engine = create_db_engine(settings)
        self.session_factory = create_db_session_factory(self.engine)
        self.read_repository = SQLModelSessionReadRepository(self.session_factory)
        self.owner_user_id = self._get_bootstrap_user_id()

    def teardown_method(self):
        self.engine.dispose()
        self._temp_dir.cleanup()

    def _get_bootstrap_user_id(self) -> str:
        with self.session_factory() as session:
            user = session.exec(
                select(DbUserRecord).where(DbUserRecord.username == "admin")
            ).one()
            return user.id.hex

    async def test_create_get_revoke_flow(self):
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            repository = SQLModelSessionMutationRepository(session)
            created = await repository.create(
                AuthSessionCreateInput(
                    sid="sid-1",
                    user_id=self.owner_user_id,
                    created_at=now,
                    expires_at=now + timedelta(hours=1),
                )
            )
            revoked = await repository.revoke_by_sid("sid-1")
            session.commit()

        assert created.user_id == self.owner_user_id
        assert revoked is not None
        assert revoked.user_id == self.owner_user_id
        assert revoked.revoked_at is not None

        fetched = await self.read_repository.get_by_sid("sid-1")
        assert fetched is not None
        assert fetched.user_id == self.owner_user_id
