"""Email endpoints – accounts, signatures, send, inbox."""
import smtplib
import imaplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.email_account import EmailAccount
from app.models.email_signature import EmailSignature
from app.models.email_message import EmailMessage
from app.schemas.email import (
    EmailAccountCreate, EmailAccountUpdate, EmailAccountResponse,
    EmailSignatureCreate, EmailSignatureUpdate, EmailSignatureResponse,
    EmailSend, EmailMessageResponse,
)

router = APIRouter(prefix="/email", tags=["email"])


# ═══════════════════════════════════════════
#  EMAIL ACCOUNTS
# ═══════════════════════════════════════════

@router.get("/accounts", response_model=List[EmailAccountResponse])
def list_accounts(user_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(EmailAccount).filter(EmailAccount.user_id == user_id).all()


@router.post("/accounts", response_model=EmailAccountResponse)
def create_account(data: EmailAccountCreate, db: Session = Depends(get_db)):
    acc = EmailAccount(**data.model_dump())
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@router.put("/accounts/{account_id}", response_model=EmailAccountResponse)
def update_account(account_id: int, data: EmailAccountUpdate, db: Session = Depends(get_db)):
    acc = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if not acc:
        raise HTTPException(404, "Account not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(acc, k, v)
    db.commit()
    db.refresh(acc)
    return acc


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if not acc:
        raise HTTPException(404, "Account not found")
    db.delete(acc)
    db.commit()
    return {"ok": True}


@router.post("/accounts/{account_id}/test")
def test_account(account_id: int, db: Session = Depends(get_db)):
    """Test SMTP and IMAP connectivity."""
    acc = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if not acc:
        raise HTTPException(404, "Account not found")

    results = {"smtp": "not_tested", "imap": "not_tested"}

    # Test SMTP
    try:
        if acc.smtp_ssl and acc.smtp_port == 465:
            server = smtplib.SMTP_SSL(acc.smtp_host, acc.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=10)
            if acc.smtp_ssl:
                server.starttls()
        server.login(acc.smtp_user, acc.smtp_password)
        server.quit()
        results["smtp"] = "ok"
    except Exception as e:
        results["smtp"] = f"error: {str(e)}"

    # Test IMAP
    if acc.imap_host and acc.imap_user:
        try:
            if acc.imap_ssl:
                mail = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port)
            else:
                mail = imaplib.IMAP4(acc.imap_host, acc.imap_port)
            mail.login(acc.imap_user, acc.imap_password)
            mail.logout()
            results["imap"] = "ok"
        except Exception as e:
            results["imap"] = f"error: {str(e)}"

    return results


# ═══════════════════════════════════════════
#  EMAIL SIGNATURES
# ═══════════════════════════════════════════

@router.get("/signatures", response_model=List[EmailSignatureResponse])
def list_signatures(user_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(EmailSignature).filter(EmailSignature.user_id == user_id).order_by(EmailSignature.created_at.desc()).all()


@router.post("/signatures", response_model=EmailSignatureResponse)
def create_signature(data: EmailSignatureCreate, db: Session = Depends(get_db)):
    sig = EmailSignature(**data.model_dump())
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


@router.put("/signatures/{sig_id}", response_model=EmailSignatureResponse)
def update_signature(sig_id: int, data: EmailSignatureUpdate, db: Session = Depends(get_db)):
    sig = db.query(EmailSignature).filter(EmailSignature.id == sig_id).first()
    if not sig:
        raise HTTPException(404, "Signature not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sig, k, v)
    db.commit()
    db.refresh(sig)
    return sig


@router.delete("/signatures/{sig_id}")
def delete_signature(sig_id: int, db: Session = Depends(get_db)):
    sig = db.query(EmailSignature).filter(EmailSignature.id == sig_id).first()
    if not sig:
        raise HTTPException(404, "Signature not found")
    db.delete(sig)
    db.commit()
    return {"ok": True}


# ═══════════════════════════════════════════
#  SEND EMAIL
# ═══════════════════════════════════════════

@router.post("/send", response_model=EmailMessageResponse)
def send_email(data: EmailSend, db: Session = Depends(get_db)):
    acc = db.query(EmailAccount).filter(EmailAccount.id == data.account_id).first()
    if not acc:
        raise HTTPException(404, "Account not found")

    # Build body with optional signature
    body_html = data.body_html or ""
    if data.signature_id:
        sig = db.query(EmailSignature).filter(EmailSignature.id == data.signature_id).first()
        if sig:
            body_html += f'<br/><br/><div class="email-signature">{sig.html_content}</div>'

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{acc.display_name or acc.email_address} <{acc.email_address}>"
    msg["To"] = data.to
    if data.cc:
        msg["Cc"] = data.cc
    msg["Subject"] = data.subject
    msg["Date"] = formatdate(localtime=True)
    msg_id = make_msgid()
    msg["Message-ID"] = msg_id

    # Plain text fallback
    import re
    plain = re.sub(r'<[^>]+>', '', body_html)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # All recipients
    all_to = [a.strip() for a in data.to.split(",")]
    if data.cc:
        all_to += [a.strip() for a in data.cc.split(",")]
    if data.bcc:
        all_to += [a.strip() for a in data.bcc.split(",")]

    # Send via SMTP
    try:
        if acc.smtp_ssl and acc.smtp_port == 465:
            server = smtplib.SMTP_SSL(acc.smtp_host, acc.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=15)
            if acc.smtp_ssl:
                server.starttls()
        server.login(acc.smtp_user, acc.smtp_password)
        server.sendmail(acc.email_address, all_to, msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(500, f"SMTP error: {str(e)}")

    # Store in DB
    now = datetime.now(timezone.utc)
    stored = EmailMessage(
        user_id=acc.user_id,
        account_id=acc.id,
        folder="sent",
        message_id=msg_id,
        subject=data.subject,
        from_address=acc.email_address,
        to_addresses=data.to,
        cc_addresses=data.cc,
        bcc_addresses=data.bcc,
        body_html=body_html,
        body_text=plain,
        is_read=True,
        sent_at=now,
    )
    db.add(stored)
    db.commit()
    db.refresh(stored)
    return stored


# ═══════════════════════════════════════════
#  INBOX – DB-first architecture
#  GET /inbox  → instant read from PostgreSQL
#  POST /inbox/sync → fetch only NEW emails from IMAP into DB
# ═══════════════════════════════════════════

@router.get("/inbox")
def get_inbox(account_id: int = Query(...), db: Session = Depends(get_db)):
    """Serve cached emails from PostgreSQL – instant, no IMAP connection."""
    messages = (
        db.query(EmailMessage)
        .filter(EmailMessage.account_id == account_id, EmailMessage.folder == "inbox")
        .order_by(EmailMessage.received_at.desc().nullslast())
        .all()
    )
    total_count = len(messages)
    unread_count = sum(1 for m in messages if not m.is_read)
    return {"messages": messages, "total_count": total_count, "unread_count": unread_count}


@router.post("/inbox/sync")
def sync_inbox(account_id: int = Query(...), db: Session = Depends(get_db)):
    """Connect to IMAP, identify NEW emails not in DB, fetch & store them.
    Returns count of new emails added."""
    acc = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if not acc or not acc.imap_host:
        raise HTTPException(400, "IMAP not configured for this account")

    from email.utils import parsedate_to_datetime
    from email.header import decode_header

    try:
        if acc.imap_ssl:
            mail = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port)
        else:
            mail = imaplib.IMAP4(acc.imap_host, acc.imap_port)
        mail.login(acc.imap_user or acc.smtp_user, acc.imap_password or acc.smtp_password)
        mail.select("INBOX")

        # Get all IMAP message IDs
        _, data = mail.search(None, "ALL")
        all_imap_ids = data[0].split()
        total_on_server = len(all_imap_ids)

        # Get existing message_ids from DB for this account
        existing_mids = set(
            row[0] for row in
            db.query(EmailMessage.message_id)
            .filter(EmailMessage.account_id == acc.id, EmailMessage.folder == "inbox")
            .all()
            if row[0]
        )

        # Process from newest to oldest, fetch headers first to check Message-ID
        new_count = 0
        # Take the latest 500 for initial check (or all if fewer)
        check_ids = all_imap_ids[-500:] if len(all_imap_ids) > 500 else all_imap_ids
        check_ids = list(reversed(check_ids))

        for eid in check_ids:
            try:
                # Fetch just the header first to get Message-ID cheaply
                _, header_data = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
                if not header_data or not header_data[0]:
                    continue

                header_raw = header_data[0][1] if isinstance(header_data[0], tuple) else b""
                header_parsed = email_lib.message_from_bytes(header_raw)
                mid = header_parsed.get("Message-ID", "").strip()

                # Skip if already in DB
                if mid and mid in existing_mids:
                    continue

                # New email – fetch full content
                _, msg_data = mail.fetch(eid, "(RFC822 FLAGS)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                parsed = email_lib.message_from_bytes(raw)

                full_mid = parsed.get("Message-ID", "").strip()
                # Double-check in case header fetch missed it
                if full_mid and full_mid in existing_mids:
                    continue

                # Extract body
                body_html = ""
                body_text = ""
                if parsed.is_multipart():
                    for part in parsed.walk():
                        ct = part.get_content_type()
                        if ct == "text/html":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_html = payload.decode("utf-8", errors="replace")
                        elif ct == "text/plain" and not body_text:
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_text = payload.decode("utf-8", errors="replace")
                else:
                    payload = parsed.get_payload(decode=True)
                    if payload:
                        decoded = payload.decode("utf-8", errors="replace")
                        if parsed.get_content_type() == "text/html":
                            body_html = decoded
                        else:
                            body_text = decoded

                # Parse date
                date_str = parsed.get("Date", "")
                received_at = None
                try:
                    received_at = parsedate_to_datetime(date_str)
                except Exception:
                    pass

                # Decode subject
                subject_raw = parsed.get("Subject", "")
                decoded_parts = decode_header(subject_raw)
                subject = ""
                for part_data, charset in decoded_parts:
                    if isinstance(part_data, bytes):
                        subject += part_data.decode(charset or "utf-8", errors="replace")
                    else:
                        subject += part_data

                # Decode From
                from_raw = parsed.get("From", "")
                decoded_from_parts = decode_header(from_raw)
                from_addr = ""
                for part_data, charset in decoded_from_parts:
                    if isinstance(part_data, bytes):
                        from_addr += part_data.decode(charset or "utf-8", errors="replace")
                    else:
                        from_addr += part_data

                # Check flags for read status
                flags_data = msg_data[0][0] if isinstance(msg_data[0], tuple) else b""
                is_read = b"\\Seen" in flags_data

                stored = EmailMessage(
                    user_id=acc.user_id,
                    account_id=acc.id,
                    folder="inbox",
                    message_id=full_mid or mid,
                    subject=subject,
                    from_address=from_addr,
                    to_addresses=parsed.get("To", ""),
                    cc_addresses=parsed.get("Cc"),
                    body_html=body_html,
                    body_text=body_text,
                    is_read=is_read,
                    received_at=received_at,
                )
                db.add(stored)
                db.commit()
                existing_mids.add(full_mid or mid)
                new_count += 1

            except Exception:
                # Skip individual email errors, continue with next
                continue

        mail.logout()
        return {"new_count": new_count, "total_on_server": total_on_server}

    except imaplib.IMAP4.error as e:
        raise HTTPException(500, f"IMAP error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Error syncing inbox: {str(e)}")


# ═══════════════════════════════════════════
#  SENT MESSAGES (from DB)
# ═══════════════════════════════════════════

@router.get("/sent", response_model=List[EmailMessageResponse])
def get_sent(user_id: int = Query(...), account_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(EmailMessage).filter(EmailMessage.user_id == user_id, EmailMessage.folder == "sent")
    if account_id:
        q = q.filter(EmailMessage.account_id == account_id)
    return q.order_by(EmailMessage.sent_at.desc()).limit(100).all()


@router.get("/messages/{msg_id}", response_model=EmailMessageResponse)
def get_message(msg_id: int, db: Session = Depends(get_db)):
    msg = db.query(EmailMessage).filter(EmailMessage.id == msg_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    if not msg.is_read:
        msg.is_read = True
        db.commit()
        db.refresh(msg)
    return msg


@router.put("/messages/{msg_id}/star")
def toggle_star(msg_id: int, db: Session = Depends(get_db)):
    msg = db.query(EmailMessage).filter(EmailMessage.id == msg_id).first()
    if not msg:
        raise HTTPException(404)
    msg.is_starred = not msg.is_starred
    db.commit()
    return {"is_starred": msg.is_starred}


@router.delete("/messages/{msg_id}")
def delete_message(msg_id: int, db: Session = Depends(get_db)):
    msg = db.query(EmailMessage).filter(EmailMessage.id == msg_id).first()
    if not msg:
        raise HTTPException(404)
    db.delete(msg)
    db.commit()
    return {"ok": True}
