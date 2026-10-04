from app.core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID 
import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    filename = Column(
        String(255),
        nullable=False
    )

    file_path = Column(
        String(255),
        nullable=False
    )
    file_size = Column(
        Integer,
        nullable=False
    )
    file_type = Column(
        String(100),
        nullable=False
    )
    file_hash = Column(
        String(64),
        nullable=True,
        index=True
    )
    status = Column(
        String(20),
        default="PENDING",
        nullable=False
    )
    error_message = Column(
        Text,
        nullable=True
    )
    chunk_count = Column(
        Integer,
        default=0,
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
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
        back_populates="documents"
    )
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index"
    )
    chat_sessions = relationship(
        "ChatSession",
        back_populates="document"
    )
    sessions = relationship(
        "ChatSession",
        secondary="session_documents",
        back_populates="documents",
        lazy="selectin",
        viewonly=True
    )
    