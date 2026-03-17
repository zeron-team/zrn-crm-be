from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class BotFlow(Base):
    __tablename__ = "bot_flows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)

    # Trigger config
    trigger_type = Column(String(50), default="keyword")  # keyword, any, first_message
    trigger_value = Column(String(500), nullable=True)     # keyword(s) or regex

    # Flow graph — stored as JSON compatible with React Flow
    nodes = Column(JSONB, default=list)
    edges = Column(JSONB, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
