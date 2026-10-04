from app.core.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID 
import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.session_document import session_documents

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    title = Column(
        String(255),
        default="Cuộc trò chuyện mới",
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
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
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="chat_sessions"
    )
    document = relationship(
        "Document",
        back_populates="chat_sessions"
    )
    documents = relationship(
        "Document",
        secondary=session_documents,
        back_populates="sessions",
        lazy="selectin",
        viewonly=True
    )
    chat_messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )