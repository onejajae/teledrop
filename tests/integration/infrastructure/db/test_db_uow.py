import pytest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from app.application.drop.ports import DropCreateInput
from app.domain.drop.value_objects import AccessScope
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.db.init import init_db
from app.infrastructure.db.repositories import SQLModelDropRepository
from app.infrastructure.db.uow_drop import SQLModelDropUnitOfWork

def _drop_create_input(slug: str) -> DropCreateInput:
    return DropCreateInput(slug=slug, access_scope=AccessScope.PRIVATE, is_favorite=False, drop_password=None, file_name=f'{slug}.txt', mime_type='text/plain', size_bytes=3, sha256=f'sha-{slug}', storage_key=f'storage-{slug}', title=slug, description=None)

class TestDropUnitOfWork:

    def setup_method(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / 'uow.db'
        settings = SimpleNamespace(SQLITE_HOST=f'sqlite:///{db_path.as_posix()}')
        self.engine = create_db_engine(settings)
        init_db(self.engine)
        self.session_factory = create_db_session_factory(self.engine)
        self.read_repository = SQLModelDropRepository(self.session_factory)

    def teardown_method(self):
        self.engine.dispose()
        self._temp_dir.cleanup()

    async def test_drop_uow_commit_persists_writes(self):
        async with SQLModelDropUnitOfWork(self.session_factory) as uow:
            await uow.repository.create(_drop_create_input('commit-slug'))
            await uow.commit()
        persisted = await self.read_repository.get_by_slug('commit-slug')
        assert persisted is not None

    async def test_drop_uow_rolls_back_when_exception_occurs(self):
        with pytest.raises(RuntimeError):
            async with SQLModelDropUnitOfWork(self.session_factory) as uow:
                await uow.repository.create(_drop_create_input('rollback-slug'))
                raise RuntimeError('force rollback')
        persisted = await self.read_repository.get_by_slug('rollback-slug')
        assert persisted is None
