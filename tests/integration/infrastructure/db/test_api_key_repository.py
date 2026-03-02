import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.application.auth.ports import AuthApiKeyCreateInput
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.db.init import init_db
from app.infrastructure.db.repositories.api_key_repository import SQLModelApiKeyRepository


class TestApiKeyRepository:
    def setup_method(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "api-keys.db"
        settings = SimpleNamespace(SQLITE_HOST=f"sqlite:///{db_path.as_posix()}")
        self.engine = create_db_engine(settings)
        init_db(self.engine)
        self.session_factory = create_db_session_factory(self.engine)
        self.repository = SQLModelApiKeyRepository(self.session_factory)

    def teardown_method(self):
        self.engine.dispose()
        self._temp_dir.cleanup()

    async def test_create_get_touch_revoke_delete_flow(self):
        now = datetime.now(timezone.utc)
        created = await self.repository.create(
            AuthApiKeyCreateInput(
                public_id="pub1",
                name="shortcuts",
                created_by_username="admin",
                key_hash="hash-1",
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
        )

        assert created.public_id == "pub1"
        fetched = await self.repository.get_by_public_id("pub1")
        assert fetched is not None
        assert fetched.name == "shortcuts"

        touched = await self.repository.touch_last_used_at("pub1", used_at=now + timedelta(minutes=1))
        assert touched is not None
        assert touched.last_used_at is not None

        revoked = await self.repository.revoke_by_public_id(
            "pub1",
            revoked_at=now + timedelta(minutes=2),
        )
        assert revoked is not None
        assert revoked.revoked_at is not None

        listed = await self.repository.list_all()
        assert len(listed) == 1
        assert listed[0].public_id == "pub1"

        deleted = await self.repository.delete_by_public_id("pub1")
        assert deleted
        assert await self.repository.get_by_public_id("pub1") is None
