from tortoise import fields, models
from .leads import Lead
from enum import Enum

class StageEnum(str, Enum):
    FREEZING = "freezing"
    COLD = "cold"
    LUKEWARM = "lukewarm"
    WARM = "warm"
    HOT = "hot"
    FIRE = "fire"
    BURNT = "nurnt"

class Stages(models.Model):
    id = fields.IntField(pk=True)

    stage = fields.CharEnumField(
        enum_type=StageEnum,
        default=StageEnum.FREEZING,
        null=False,
    )
    lead_id = fields.ForeignKeyField(
        "models.Lead",
        related_name="stages",
        null=True,
        on_delete=fields.SET_NULL,
    )
    class Meta: #type: ignore
        table = 'stages'