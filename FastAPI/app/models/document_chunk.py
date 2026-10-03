from app.core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_index = Column(
        Integer,
        nullable=False
    )
    content = Column(
        Text,
        nullable=False
    )
    vector_id = Column(
        String(100),
        nullable=True,
        index=True
    )
    chunk_metadata = Column(
        JSON,
        nullable=True
    )
    token_count = Column(
        Integer,
        nullable=True
    )
    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    document = relationship(
        "Document",
        back_populates="chunks"
    )
