from tortoise import fields, models


class User(models.Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True)
    firstname = fields.CharField(max_length=100)
    lastname = fields.CharField(max_length=100, null=True)
    can_review = fields.BooleanField(default=False)

    disabled = fields.BooleanField(default=False)

    class Meta: #type: ignore
        table = 'users'

    