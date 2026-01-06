from tortoise import fields, models


class Thread(models.Model):
    id = fields.IntField(pk=True)
    lead = fields.ForeignKeyField(
        "models.Lead",
        related_name="threads",
        on_delete=fields.CASCADE,
    )
    source = fields.CharField(max_length=20)
    collected_by = fields.ForeignKeyField(
        "models.User",
        related_name="collected_threads",
        null=True,
        on_delete=fields.SET_NULL,
    )
    collected_at = fields.DatetimeField(null=True)
    external_thread_id = fields.CharField(max_length=255, null=True)
    thread_fingerprint = fields.CharField(max_length=64, null=True)

    class Meta:  # type: ignore
        table = "threads"
        indexes = [
            ("lead_id", "source", "external_thread_id"),
            ("thread_fingerprint",),
        ]


class ThreadMessage(models.Model):
    id = fields.IntField(pk=True)
    thread = fields.ForeignKeyField(
        "models.Thread",
        related_name="messages",
        on_delete=fields.CASCADE,
    )
    source = fields.CharField(max_length=20)
    direction = fields.CharField(max_length=20)
    message_at = fields.DatetimeField(null=True)
    encrypted_content = fields.BinaryField()
    content_hash = fields.CharField(max_length=64, null=True)
    external_message_id = fields.CharField(max_length=255, null=True)

    class Meta:  # type: ignore
        table = "thread_messages"
        indexes = [
            ("thread_id", "external_message_id"),
            ("content_hash",),
        ]
