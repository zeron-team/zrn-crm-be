from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email_address = Column(String, nullable=False)
    display_name = Column(String, nullable=True)

    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String, nullable=False)
    smtp_password = Column(String, nullable=False)
    smtp_ssl = Column(Boolean, default=True)

    imap_host = Column(String, nullable=True)
    imap_port = Column(Integer, default=993)
    imap_user = Column(String, nullable=True)
    imap_password = Column(String, nullable=True)
    imap_ssl = Column(Boolean, default=True)

    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
