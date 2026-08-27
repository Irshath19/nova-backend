import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.concept import note_concepts
from app.models.tag import note_tags
from app.models.types import VectorType


class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="Untitled Note")
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(500), nullable=True)
    processing_status = Column(
        Enum(ProcessingStatus, name="processing_status_enum"),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )
    embedding = Column(VectorType(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="notes")
    tags = relationship("Tag", secondary=note_tags, back_populates="notes")
    concepts = relationship("Concept", secondary=note_concepts, back_populates="notes")
