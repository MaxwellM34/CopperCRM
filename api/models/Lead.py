from tortoise import fields, models


class Lead(models.Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True)
    work_email = fields.CharField(max_length=255, unique=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100, null=True)


    class Meta: #type: ignore
        table = 'Leads'
from .user import User

__all__ = ["User"]
