import pytest
from unittest.mock import MagicMock

from app.infrastructure.db.uow_base import BaseSQLModelUnitOfWork


class TestBaseSQLModelUnitOfWork:
    def setup_method(self):
        self.session = MagicMock()
        self.initial_repository = object()
        self.bound_repository = object()
        self.uow = BaseSQLModelUnitOfWork(
            session_factory=lambda: self.session,
            repository_factory=lambda _session: self.bound_repository,
            initial_repository=self.initial_repository,
            inactive_session_error="inactive session",
        )

    async def test_aenter_binds_repository(self):
        returned = await self.uow.__aenter__()

        assert returned is self.uow
        assert self.uow.repository is self.bound_repository

    async def test_aexit_without_exception_closes_session(self):
        await self.uow.__aenter__()

        await self.uow.__aexit__(None, None, None)

        self.session.rollback.assert_not_called()
        self.session.close.assert_called_once_with()

    async def test_aexit_with_exception_rolls_back_and_closes_session(self):
        await self.uow.__aenter__()

        await self.uow.__aexit__(RuntimeError, RuntimeError("boom"), None)

        self.session.rollback.assert_called_once_with()
        self.session.close.assert_called_once_with()

    async def test_commit_raises_without_active_session(self):
        with pytest.raises(RuntimeError, match="inactive session"):
            await self.uow.commit()

    async def test_rollback_raises_without_active_session(self):
        with pytest.raises(RuntimeError, match="inactive session"):
            await self.uow.rollback()

    async def test_commit_and_rollback_use_active_session(self):
        await self.uow.__aenter__()

        await self.uow.commit()
        await self.uow.rollback()

        self.session.commit.assert_called_once_with()
        self.session.rollback.assert_called_once_with()
