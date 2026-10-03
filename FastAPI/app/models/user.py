from app.core.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID 
import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_name = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )    

    email = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )

    hashed_password = Column(
        String(255),
        nullable=False
    )
    
    is_active = Column(
        Boolean, 
        default=True
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

    documents = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan" 
    )
    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan" 
    )