from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Uuid, Boolean

from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(30), unique=True)
    password = Column(String)


class Content(Base):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True)
    hash = Column(String, nullable=True)
    location = Column(String)
    size = Column(Integer)
    mime = Column(String, nullable=True)
    is_url = Column(Boolean)


class Upload(Base):
    __tablename__ = "upload"

    id = Column(Integer, primary_key=True)

    title = Column(String)
    filename = Column(String)
    description = Column(String, nullable=True)
    datetime = Column(DateTime)

    key = Column(String, unique=True, index=True)
    password = Column(String, nullable=True)

    is_anonymous = Column(Boolean)
    user_only = Column(Boolean)

    content_id = Column(Integer, ForeignKey("content.id"))
    content = relationship("Content", backref="uploads")

    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    user = relationship("User", backref="uploads")
