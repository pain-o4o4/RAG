from app.core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID 
import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(
        String(20),
        nullable=False,
        comment="user, assistant, or system"
    )
    content = Column(
        Text,
        nullable=False
    )
    sources = Column(
        JSON,
        nullable=True,
        comment="Retrieved RAG citations/chunks"
    )
    model_name = Column(
        String(50),
        nullable=True
    )
    prompt_tokens = Column(
        Integer,
        nullable=True
    )
    completion_tokens = Column(
        Integer,
        nullable=True
    )
    total_tokens = Column(
        Integer,
        nullable=True
    )
    is_deleted = Column(
        Boolean,
        default=False
    )
    deleted_at = Column(
        DateTime,
        nullable=True
    )
    created_at = Column(
        DateTime,
        server_default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    session = relationship(
        "ChatSession",
        back_populates="chat_messages"
    )