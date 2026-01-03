from tortoise import fields, models


class LLMProfile(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    description = fields.TextField(null=True)
    rules = fields.TextField()
    category = fields.CharField(max_length=50, default="general")
    is_default = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # type: ignore
        table = "llm_profiles"


class Campaign(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    category = fields.CharField(max_length=50, default="cold_outbound")
    status = fields.CharField(max_length=50, default="draft")
    preset_key = fields.CharField(max_length=100, null=True)
    audience_size = fields.IntField(null=True)
    entry_point = fields.CharField(max_length=255, null=True)
    ai_brief = fields.TextField(null=True)
    launch_notes = fields.TextField(null=True)
    launched_at = fields.DatetimeField(null=True)
    llm_profile = fields.ForeignKeyField(
        "models.LLMProfile",
        related_name="campaigns",
        null=True,
        on_delete=fields.SET_NULL,
    )
    llm_overlay_profile = fields.ForeignKeyField(
        "models.LLMProfile",
        related_name="overlay_campaigns",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_campaigns",
        null=True,
        on_delete=fields.SET_NULL,
    )
    updated_by = fields.ForeignKeyField(
        "models.User",
        related_name="updated_campaigns",
        null=True,
        on_delete=fields.SET_NULL,
    )
    launched_by = fields.ForeignKeyField(
        "models.User",
        related_name="launched_campaigns",
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:  # type: ignore
        table = "campaigns"


class CampaignStep(models.Model):
    id = fields.IntField(pk=True)
    campaign = fields.ForeignKeyField(
        "models.Campaign",
        related_name="steps",
        on_delete=fields.CASCADE,
    )
    title = fields.CharField(max_length=255)
    step_type = fields.CharField(max_length=50)
    sequence = fields.IntField(default=1)
    lane = fields.CharField(max_length=50, null=True)
    prompt_template = fields.TextField(null=True)
    config = fields.JSONField(default=dict)
    position_x = fields.IntField(null=True)
    position_y = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # type: ignore
        table = "campaign_steps"
        ordering = ["sequence", "id"]
        unique_together = (("campaign", "sequence", "title"),)
