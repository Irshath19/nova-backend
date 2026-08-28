import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.types import VectorType

# Many-to-Many association table for Note <-> Concept
note_concepts = Table(
    "note_concepts",
    Base.metadata,
    Column("note_id", String(36), ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("concept_id", String(36), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
)


class KnowledgeLevel(str, enum.Enum):
    NEW = "NEW"
    FAMILIAR = "FAMILIAR"
    LEARNING = "LEARNING"
    INTERMEDIATE = "INTERMEDIATE"
    STRONG = "STRONG"


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_concept_name"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    knowledge_level = Column(
        Enum(KnowledgeLevel, name="knowledge_level_enum"),
        default=KnowledgeLevel.NEW,
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
    user = relationship("User", back_populates="concepts")
    notes = relationship("Note", secondary=note_concepts, back_populates="concepts")
    outgoing_relationships = relationship(
        "ConceptRelationship",
        foreign_keys="ConceptRelationship.source_concept_id",
        back_populates="source_concept",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "ConceptRelationship",
        foreign_keys="ConceptRelationship.target_concept_id",
        back_populates="target_concept",
        cascade="all, delete-orphan",
    )
    learning_path_items = relationship(
        "LearningPathItem",
        back_populates="concept",
        cascade="all, delete-orphan",
    )
