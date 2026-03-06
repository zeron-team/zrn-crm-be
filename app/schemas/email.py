from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Email Account ──
class EmailAccountCreate(BaseModel):
    user_id: int
    email_address: str
    display_name: Optional[str] = None
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_ssl: bool = True
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_ssl: bool = True
    is_default: bool = False


class EmailAccountUpdate(BaseModel):
    email_address: Optional[str] = None
    display_name: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_ssl: Optional[bool] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_ssl: Optional[bool] = None
    is_default: Optional[bool] = None


class EmailAccountResponse(BaseModel):
    id: int
    user_id: int
    email_address: str
    display_name: Optional[str] = None
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_ssl: bool
    imap_host: Optional[str] = None
    imap_port: int
    imap_ssl: bool
    is_default: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Email Signature ──
class EmailSignatureCreate(BaseModel):
    user_id: int
    name: str
    html_content: str = ""
    is_default: bool = False


class EmailSignatureUpdate(BaseModel):
    name: Optional[str] = None
    html_content: Optional[str] = None
    is_default: Optional[bool] = None


class EmailSignatureResponse(BaseModel):
    id: int
    user_id: int
    name: str
    html_content: str
    is_default: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Email Message ──
class EmailSend(BaseModel):
    account_id: int
    to: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    subject: str = ""
    body_html: str = ""
    signature_id: Optional[int] = None


class EmailMessageResponse(BaseModel):
    id: int
    user_id: int
    account_id: Optional[int] = None
    folder: str
    message_id: Optional[str] = None
    subject: Optional[str] = None
    from_address: str
    to_addresses: str
    cc_addresses: Optional[str] = None
    bcc_addresses: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    is_read: bool
    is_starred: bool
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
