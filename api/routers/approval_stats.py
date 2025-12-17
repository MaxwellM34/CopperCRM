from fastapi import APIRouter
from pydantic import BaseModel
from tortoise.expressions import Q

from models import FirstEmail

router = APIRouter(prefix="/approval-stats", tags=["first-emails"])


class ApprovalStats(BaseModel):
    pending_for_approval: int


@router.get("/", response_model=ApprovalStats)
async def get_approval_stats():
    pending = await FirstEmail.filter(Q(approval_record__human_reviewed=False) | Q(approval_record=None)).count()
    return ApprovalStats(pending_for_approval=pending)
