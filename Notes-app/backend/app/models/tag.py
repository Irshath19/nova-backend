import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base

# Many-to-Many association table for Note <-> Tag
note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", String(36), ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_tag_name"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    user = relationship("User", back_populates="tags")
    notes = relationship("Note", secondary=note_tags, back_populates="tags")
