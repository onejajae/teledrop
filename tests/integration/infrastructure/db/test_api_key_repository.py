import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.application.auth.ports import AuthApiKeyCreateInput
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
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

    def teardown_method(self):
        self.engine.dispose()
        self._temp_dir.cleanup()

    async def test_create_get_touch_revoke_delete_flow(self):
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            repository = SQLModelApiKeyMutationRepository(session)
            created = await repository.create(
                AuthApiKeyCreateInput(
                    public_id="pub1",
                    name="shortcuts",
                    created_by_username="admin",
                    key_hash="hash-1",
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                )
            )
            await repository.touch_last_used_at("pub1", used_at=now + timedelta(minutes=1))
            await repository.revoke_by_public_id(
                "pub1",
                revoked_at=now + timedelta(minutes=2),
            )
            session.commit()

        assert created.public_id == "pub1"
        fetched = await self.read_repository.get_by_public_id("pub1")
        assert fetched is not None
        assert fetched.name == "shortcuts"
        assert fetched.last_used_at is not None
        assert fetched.revoked_at is not None

        listed = await self.read_repository.list_all()
        assert len(listed) == 1
        assert listed[0].public_id == "pub1"

        with self.session_factory() as session:
            repository = SQLModelApiKeyMutationRepository(session)
            deleted = await repository.delete_by_public_id("pub1")
            session.commit()
        assert deleted
        assert await self.read_repository.get_by_public_id("pub1") is None
