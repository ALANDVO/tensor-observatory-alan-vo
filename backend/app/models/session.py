"""Session model (separate to avoid circular imports)."""

from sqlalchemy import Column, String, Text, BigInteger, Index
from sqlalchemy.orm import declarative_base

# Use the same Base from database
from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    roles = Column(Text, nullable=False, default="[]")
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False, default="")
    expires_at = Column(BigInteger, nullable=False)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("ix_sessions_expires_at", "expires_at"),
        Index("ix_sessions_user_id", "user_id"),
    )