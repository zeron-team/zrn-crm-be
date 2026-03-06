from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("email_accounts.id"), nullable=True)
    folder = Column(String, default="sent", index=True)  # inbox, sent, draft
    message_id = Column(String, nullable=True)  # RFC Message-ID
    subject = Column(String, nullable=True, default="")
    from_address = Column(String, nullable=False)
    to_addresses = Column(Text, nullable=False)  # comma-separated
    cc_addresses = Column(Text, nullable=True)
    bcc_addresses = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    is_read = Column(Boolean, default=True)
    is_starred = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
