"""Wiki page model — documentation pages linked to any entity."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=True, default="")
    slug = Column(String(500), nullable=True, index=True)

    # Flexible association: entity_type + entity_id
    entity_type = Column(String(50), nullable=True, index=True)   # project, client, lead, provider, ticket, general
    entity_id = Column(Integer, nullable=True, index=True)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey("wiki_pages.id", ondelete="SET NULL"), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    children = relationship("WikiPage", backref="parent", remote_side="WikiPage.id",
                            foreign_keys=[parent_id])
