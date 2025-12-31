from tortoise import fields, models
from .leads import Lead

class Stages(models.Model):
    id = fields.IntField(pk=True)
    lead_id = fields.ForeignKeyField(
        "models.Lead",
        related_name="stages",
        null=True,
        on_delete=fields.SET_NULL,
    )
    class Meta: #type: ignore
        table = 'stages'