from tortoise import fields, models


class OutboundInbox(models.Model):
    id = fields.IntField(pk=True)
    email_address = fields.CharField(max_length=255, unique=True)
    display_name = fields.CharField(max_length=255, null=True)
    domain = fields.CharField(max_length=255)
    subdomain = fields.CharField(max_length=255, null=True)
    ses_identity = fields.CharField(max_length=255, null=True)
    ses_configuration_set = fields.CharField(max_length=255, null=True)
    daily_cap = fields.IntField(default=200)
    daily_sent = fields.IntField(default=0)
    last_reset_at = fields.DatetimeField(null=True)
    active = fields.BooleanField(default=True)
    imap_host = fields.CharField(max_length=255, null=True)
    imap_port = fields.IntField(null=True)
    imap_use_ssl = fields.BooleanField(default=True)
    imap_username = fields.CharField(max_length=255, null=True)
    imap_password = fields.CharField(max_length=255, null=True)
    imap_folder = fields.CharField(max_length=255, null=True)
    imap_sent_folder = fields.CharField(max_length=255, null=True)
    imap_last_uid = fields.IntField(null=True)
    imap_last_checked_at = fields.DatetimeField(null=True)
    reply_to = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # type: ignore
        table = "outbound_inboxes"


class CampaignEdge(models.Model):
    id = fields.IntField(pk=True)
    campaign = fields.ForeignKeyField(
        "models.Campaign",
        related_name="edges",
        on_delete=fields.CASCADE,
    )
    from_step = fields.ForeignKeyField(
        "models.CampaignStep",
        related_name="outgoing_edges",
        on_delete=fields.CASCADE,
    )
    to_step = fields.ForeignKeyField(
        "models.CampaignStep",
        related_name="incoming_edges",
        on_delete=fields.CASCADE,
    )
    condition_type = fields.CharField(max_length=50, default="always")
    condition_value = fields.TextField(null=True)
    label = fields.CharField(max_length=255, null=True)
    order = fields.IntField(default=1)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # type: ignore
        table = "campaign_edges"


class LeadCampaignState(models.Model):
    id = fields.IntField(pk=True)
    lead = fields.ForeignKeyField(
        "models.Lead",
        related_name="campaign_states",
        on_delete=fields.CASCADE,
    )
    campaign = fields.ForeignKeyField(
        "models.Campaign",
        related_name="lead_states",
        on_delete=fields.CASCADE,
    )
    status = fields.CharField(max_length=50, default="pending")
    current_step = fields.ForeignKeyField(
        "models.CampaignStep",
        related_name="lead_states",
        null=True,
        on_delete=fields.SET_NULL,
    )
    assigned_inbox = fields.ForeignKeyField(
        "models.OutboundInbox",
        related_name="assigned_leads",
        null=True,
        on_delete=fields.SET_NULL,
    )
    next_step_at = fields.DatetimeField(null=True)
    last_sent_at = fields.DatetimeField(null=True)
    last_activity_at = fields.DatetimeField(null=True)
    thread_id = fields.CharField(max_length=255, null=True)
    last_message_id = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # type: ignore
        table = "lead_campaign_states"
        unique_together = (("lead", "campaign"),)


class LeadActivity(models.Model):
    id = fields.IntField(pk=True)
    lead = fields.ForeignKeyField(
        "models.Lead",
        related_name="activities",
        on_delete=fields.CASCADE,
    )
    campaign = fields.ForeignKeyField(
        "models.Campaign",
        related_name="activities",
        null=True,
        on_delete=fields.SET_NULL,
    )
    inbox = fields.ForeignKeyField(
        "models.OutboundInbox",
        related_name="activities",
        null=True,
        on_delete=fields.SET_NULL,
    )
    activity_type = fields.CharField(max_length=50)
    occurred_at = fields.DatetimeField(auto_now_add=True)
    metadata = fields.JSONField(default=dict)

    class Meta:  # type: ignore
        table = "lead_activities"


class OutboundMessage(models.Model):
    id = fields.IntField(pk=True)
    lead = fields.ForeignKeyField(
        "models.Lead",
        related_name="messages",
        on_delete=fields.CASCADE,
    )
    campaign = fields.ForeignKeyField(
        "models.Campaign",
        related_name="messages",
        null=True,
        on_delete=fields.SET_NULL,
    )
    inbox = fields.ForeignKeyField(
        "models.OutboundInbox",
        related_name="messages",
        null=True,
        on_delete=fields.SET_NULL,
    )
    step = fields.ForeignKeyField(
        "models.CampaignStep",
        related_name="outbound_messages",
        null=True,
        on_delete=fields.SET_NULL,
    )
    direction = fields.CharField(max_length=20, default="outbound")
    message_id = fields.CharField(max_length=255, unique=True)
    thread_id = fields.CharField(max_length=255, null=True)
    subject = fields.CharField(max_length=255, null=True)
    in_reply_to = fields.CharField(max_length=255, null=True)
    references = fields.TextField(null=True)
    sent_at = fields.DatetimeField(null=True)
    status = fields.CharField(max_length=50, default="sent")
    recipient_email = fields.CharField(max_length=255, null=True)
    tracking_id = fields.CharField(max_length=255, null=True, unique=True)
    llm_profile_version = fields.CharField(max_length=100, null=True)
    llm_profile_name = fields.CharField(max_length=255, null=True)
    llm_profile_rules = fields.TextField(null=True)
    llm_overlay_profile_version = fields.CharField(max_length=100, null=True)
    llm_overlay_profile_name = fields.CharField(max_length=255, null=True)
    llm_overlay_profile_rules = fields.TextField(null=True)
    first_opened_at = fields.DatetimeField(null=True)
    last_opened_at = fields.DatetimeField(null=True)
    open_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # type: ignore
        table = "outbound_messages"


class CampaignEmailDraft(models.Model):
    id = fields.IntField(pk=True)
    campaign = fields.ForeignKeyField(
        "models.Campaign",
        related_name="email_drafts",
        on_delete=fields.CASCADE,
    )
    lead = fields.ForeignKeyField(
        "models.Lead",
        related_name="email_drafts",
        on_delete=fields.CASCADE,
    )
    inbox = fields.ForeignKeyField(
        "models.OutboundInbox",
        related_name="email_drafts",
        null=True,
        on_delete=fields.SET_NULL,
    )
    subject = fields.CharField(max_length=255, null=True)
    body_text = fields.TextField()
    body_html = fields.TextField(null=True)
    status = fields.CharField(max_length=50, default="pending")
    from_email = fields.CharField(max_length=255, null=True)
    to_email = fields.CharField(max_length=255, null=True)
    llm_profile_version = fields.CharField(max_length=100, null=True)
    llm_profile_name = fields.CharField(max_length=255, null=True)
    llm_profile_rules = fields.TextField(null=True)
    llm_overlay_profile_version = fields.CharField(max_length=100, null=True)
    llm_overlay_profile_name = fields.CharField(max_length=255, null=True)
    llm_overlay_profile_rules = fields.TextField(null=True)
    approved_by = fields.ForeignKeyField(
        "models.User",
        related_name="approved_campaign_emails",
        null=True,
        on_delete=fields.SET_NULL,
    )
    approved_at = fields.DatetimeField(null=True)
    sent_at = fields.DatetimeField(null=True)
    step = fields.ForeignKeyField(
        "models.CampaignStep",
        related_name="email_drafts",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # type: ignore
        table = "campaign_email_drafts"
