from tortoise import fields, models


class User(models.Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True)
    firstname = fields.CharField(max_length=100)
    lastname = fields.CharField(max_length=100, null=True)
    is_admin = fields.BooleanField(default=False)
    disabled = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta: #type: ignore
        table = 'users'

