import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class RelationshipType(str, enum.Enum):
    RELATED_TO = "RELATED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    PART_OF = "PART_OF"
    USES = "USES"
    LEADS_TO = "LEADS_TO"


class ConceptRelationship(Base):
    __tablename__ = "concept_relationships"
    __table_args__ = (
        UniqueConstraint("user_id", "source_concept_id", "target_concept_id", "relationship_type", name="uq_user_concept_rel"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    target_concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(
        Enum(RelationshipType, name="relationship_type_enum"),
        default=RelationshipType.RELATED_TO,
        nullable=False,
    )
    weight = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    user = relationship("User", back_populates="relationships")
    source_concept = relationship("Concept", foreign_keys=[source_concept_id], back_populates="outgoing_relationships")
    target_concept = relationship("Concept", foreign_keys=[target_concept_id], back_populates="incoming_relationships")
