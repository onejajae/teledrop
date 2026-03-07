from sqlmodel import Session


class SessionBoundMutationRepository:
    def __init__(self, session: Session, *, inactive_session_error: str):
        self._session: Session | None = session
        self._inactive_session_error = inactive_session_error

    def deactivate(self) -> None:
        self._session = None

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError(self._inactive_session_error)
        return self._session


__all__ = ["SessionBoundMutationRepository"]
