from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.authenticate import authenticate
from models import OutboundInbox, User

router = APIRouter(prefix="/outbound-inboxes", tags=["outbound-inboxes"])


class OutboundInboxPayload(BaseModel):
    email_address: str
    display_name: str | None = None
    domain: str | None = None
    subdomain: str | None = None
    ses_identity: str | None = None
    ses_configuration_set: str | None = None
    daily_cap: int = 200
    active: bool = True
    imap_host: str | None = None
    imap_port: int | None = None
    imap_use_ssl: bool = True
    imap_username: str | None = None
    imap_password: str | None = None
    imap_folder: str | None = None
    imap_sent_folder: str | None = None
    reply_to: str | None = None


class OutboundInboxResponse(BaseModel):
    id: int
    email_address: str
    display_name: str | None
    domain: str
    subdomain: str | None
    ses_identity: str | None
    ses_configuration_set: str | None
    daily_cap: int
    daily_sent: int
    active: bool
    imap_host: str | None
    imap_port: int | None
    imap_use_ssl: bool
    imap_username: str | None
    imap_folder: str | None
    imap_sent_folder: str | None
    imap_password_set: bool = Field(False)
    reply_to: str | None
    created_at: str | None = None
    updated_at: str | None = None


def _derive_domain(email_address: str) -> str:
    if "@" not in email_address:
        return email_address
    return email_address.split("@")[-1].strip().lower()


def _serialize_inbox(inbox: OutboundInbox) -> OutboundInboxResponse:
    return OutboundInboxResponse(
        id=inbox.id,  # type: ignore[arg-type]
        email_address=inbox.email_address,  # type: ignore[arg-type]
        display_name=inbox.display_name,  # type: ignore[arg-type]
        domain=inbox.domain,  # type: ignore[arg-type]
        subdomain=inbox.subdomain,  # type: ignore[arg-type]
        ses_identity=inbox.ses_identity,  # type: ignore[arg-type]
        ses_configuration_set=inbox.ses_configuration_set,  # type: ignore[arg-type]
        daily_cap=inbox.daily_cap,  # type: ignore[arg-type]
        daily_sent=inbox.daily_sent,  # type: ignore[arg-type]
        active=bool(inbox.active),
        imap_host=inbox.imap_host,  # type: ignore[arg-type]
        imap_port=inbox.imap_port,  # type: ignore[arg-type]
        imap_use_ssl=bool(inbox.imap_use_ssl),
        imap_username=inbox.imap_username,  # type: ignore[arg-type]
        imap_folder=inbox.imap_folder,  # type: ignore[arg-type]
        imap_sent_folder=inbox.imap_sent_folder,  # type: ignore[arg-type]
        imap_password_set=bool(inbox.imap_password),
        reply_to=inbox.reply_to,  # type: ignore[arg-type]
        created_at=inbox.created_at.isoformat() if inbox.created_at else None,  # type: ignore[arg-type]
        updated_at=inbox.updated_at.isoformat() if inbox.updated_at else None,  # type: ignore[arg-type]
    )


@router.get("", response_model=list[OutboundInboxResponse])
async def list_outbound_inboxes(user: User = Depends(authenticate)):
    inboxes = await OutboundInbox.all().order_by("id")
    return [_serialize_inbox(inbox) for inbox in inboxes]


@router.post("", response_model=OutboundInboxResponse)
async def create_outbound_inbox(payload: OutboundInboxPayload, user: User = Depends(authenticate)):
    domain = payload.domain or _derive_domain(payload.email_address)
    inbox = await OutboundInbox.create(
        email_address=payload.email_address,
        display_name=payload.display_name,
        domain=domain,
        subdomain=payload.subdomain,
        ses_identity=payload.ses_identity,
        ses_configuration_set=payload.ses_configuration_set,
        daily_cap=payload.daily_cap,
        active=payload.active,
        imap_host=payload.imap_host,
        imap_port=payload.imap_port,
        imap_use_ssl=payload.imap_use_ssl,
        imap_username=payload.imap_username,
        imap_password=payload.imap_password,
        imap_folder=payload.imap_folder,
        imap_sent_folder=payload.imap_sent_folder,
        reply_to=payload.reply_to,
    )
    return _serialize_inbox(inbox)


@router.put("/{inbox_id}", response_model=OutboundInboxResponse)
async def update_outbound_inbox(
    inbox_id: int,
    payload: OutboundInboxPayload,
    user: User = Depends(authenticate),
):
    inbox = await OutboundInbox.filter(id=inbox_id).first()
    if inbox is None:
        raise HTTPException(status_code=404, detail="Outbound inbox not found")

    inbox.email_address = payload.email_address  # type: ignore[assignment]
    inbox.display_name = payload.display_name  # type: ignore[assignment]
    inbox.domain = payload.domain or _derive_domain(payload.email_address)  # type: ignore[assignment]
    inbox.subdomain = payload.subdomain  # type: ignore[assignment]
    inbox.ses_identity = payload.ses_identity  # type: ignore[assignment]
    inbox.ses_configuration_set = payload.ses_configuration_set  # type: ignore[assignment]
    inbox.daily_cap = payload.daily_cap  # type: ignore[assignment]
    inbox.active = payload.active  # type: ignore[assignment]
    inbox.imap_host = payload.imap_host  # type: ignore[assignment]
    inbox.imap_port = payload.imap_port  # type: ignore[assignment]
    inbox.imap_use_ssl = payload.imap_use_ssl  # type: ignore[assignment]
    inbox.imap_username = payload.imap_username  # type: ignore[assignment]
    if payload.imap_password:
        inbox.imap_password = payload.imap_password  # type: ignore[assignment]
    inbox.imap_folder = payload.imap_folder  # type: ignore[assignment]
    inbox.imap_sent_folder = payload.imap_sent_folder  # type: ignore[assignment]
    inbox.reply_to = payload.reply_to  # type: ignore[assignment]
    await inbox.save()

    return _serialize_inbox(inbox)
