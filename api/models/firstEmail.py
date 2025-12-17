from tortoise import fields, models


class FirstEmail(models.Model):
    id = fields.IntField(pk=True)
    lead = fields.OneToOneField(
        "models.Lead",
        related_name="first_email",
        on_delete=fields.CASCADE,
    )
    first_email = fields.TextField()  # email to be sent
    approval = fields.BooleanField(default=False)
    model = fields.CharField(max_length=100, null=True)
    prompt_tokens = fields.IntField(null=True)
    completion_tokens = fields.IntField(null=True)
    total_tokens = fields.IntField(null=True)
    cost_usd = fields.DecimalField(max_digits=10, decimal_places=6, null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_first_email",
        null=True,
        on_delete=fields.SET_NULL,
    )
    updated_by = fields.ForeignKeyField(
        "models.User",
        related_name="updated_first_email",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    human_edited = fields.BooleanField(default=False)
    pre_human_edit = fields.TextField(null=True)
    post_human_edit = fields.TextField(null=True)
    pre_editor = fields.TextField(null=True)
    post_editor = fields.TextField(null=True)
    edited_by = fields.CharField(max_length=255, null=True)

    class Meta:  # type: ignore
        table = "first_email"


class FirstEmailApproval(models.Model):
    id = fields.IntField(pk=True)
    first_email = fields.OneToOneField(
        "models.FirstEmail",
        related_name="approval_record",
        on_delete=fields.CASCADE,
        null=True,
    )
    overall_approval = fields.BooleanField(default=False)
    algorithm_approval = fields.BooleanField(default=False)
    human_approval = fields.BooleanField(default=False)
    human_reviewed = fields.BooleanField(default=False)
    structure_and_clarity = fields.IntField(
        null=False,
        constraints={"structure_and_clarity BETWEEN 0 AND 7"},
    )
    deliverability = fields.IntField(
        null=False,
        constraints={"structure_and_clarity BETWEEN 0 AND 7"},
    )
    value_proposition = fields.IntField(
        null=False,
        constraints={"structure_and_clarity BETWEEN 0 AND 7"},
    )
    customer_reaction = fields.IntField(
        null=False,
        constraints={"structure_and_clarity BETWEEN 0 AND 7"},
    )

    class Meta:  # type: ignore
        table = "first_email_approvals"
