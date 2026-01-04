from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response

from models import Lead, LeadCampaignState, OutboundMessage
from services.campaign_runtime import _record_activity
from services.tracking import parse_unsubscribe_token

router = APIRouter(tags=["tracking"])


PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
    b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
    b"D\x01\x00;"
)


@router.get("/tracking/pixel/{tracking_id}.gif")
async def tracking_pixel(tracking_id: str):
    message = await OutboundMessage.filter(tracking_id=tracking_id).prefetch_related("lead", "campaign", "inbox").first()
    if message:
        if message.open_count == 0:
            message.first_opened_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        message.open_count = (message.open_count or 0) + 1  # type: ignore[assignment]
        message.last_opened_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await message.save()
        await _record_activity(
            lead=message.lead,
            campaign=message.campaign,
            inbox=message.inbox,
            activity_type="email_open",
            metadata={"message_id": message.message_id},
        )
    return Response(content=PIXEL_GIF, media_type="image/gif")


@router.get("/unsubscribe/{token}")
async def unsubscribe(token: str):
    parsed = parse_unsubscribe_token(token)
    if not parsed:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token")
    lead_id, _ = parsed
    lead = await Lead.filter(id=lead_id).first()
    if lead is None:
        return Response(content="You have been unsubscribed.", media_type="text/plain")

    lead.opted_out = True  # type: ignore[assignment]
    lead.opted_out_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    await lead.save()

    states = await LeadCampaignState.filter(lead_id=lead_id).prefetch_related("campaign", "assigned_inbox")
    for state in states:
        state.status = "stopped"  # type: ignore[assignment]
        await state.save()

    await _record_activity(
        lead=lead,
        campaign=states[0].campaign if states else None,
        inbox=states[0].assigned_inbox if states else None,
        activity_type="unsubscribe",
        metadata={"lead_id": lead_id},
    )

    return Response(content="You have been unsubscribed. Thank you.", media_type="text/plain")
