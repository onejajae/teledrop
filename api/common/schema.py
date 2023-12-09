from pydantic import BaseModel


class KeyCheck(BaseModel):
    key: str
    exist: bool
