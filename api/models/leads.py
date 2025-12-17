from tortoise import fields, models


class Lead(models.Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=100, unique=True, null=True)
    work_email = fields.CharField(max_length=100, unique=True, null=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=255)
    job_title = fields.CharField(max_length=255, null=True)
    company = fields.ForeignKeyField(
        "models.Company",
        related_name="leads",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_leads",
        null=True,
        on_delete=fields.SET_NULL,
    )
    updated_by = fields.ForeignKeyField(
        "models.User",
        related_name="updated_leads",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    work_email_status = fields.CharField(max_length=20, null=True)
    work_email_quality = fields.CharField(max_length=20, null=True)
    work_email_confidence = fields.CharField(max_length=20, null=True)
    primary_work_email_source = fields.CharField(max_length=100, null=True)
    work_email_service_provider = fields.CharField(max_length=100, null=True)
    catch_all_status = fields.BooleanField(default=False, null=True)
    person_address = fields.CharField(max_length=255, null=True)
    country = fields.CharField(max_length=100, null=True)
    personal_linkedin = fields.CharField(max_length=255, null=True)
    seniority = fields.CharField(max_length=255, null=True)
    departments = fields.CharField(max_length=255, null=True)
    industries = fields.CharField(max_length=255, null=True)
    profile_summary = fields.TextField(null=True)

    class Meta:  # type: ignore
        table = "leads"


class Company(models.Model):
    id = fields.IntField(pk=True)
    company_name = fields.CharField(max_length=255)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_companies",
        null=True,
        on_delete=fields.SET_NULL,
    )
    updated_by = fields.ForeignKeyField(
        "models.User",
        related_name="updated_companies",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    employees_amount = fields.CharField(max_length=100, null=True)
    company_address = fields.CharField(max_length=255, null=True)
    company_city = fields.CharField(max_length=255, null=True)
    company_phone = fields.CharField(max_length=255, null=True)
    company_email = fields.CharField(max_length=255, null=True)
    technologies = fields.CharField(max_length=255, null=True)
    latest_funding = fields.CharField(max_length=255, null=True)
    latest_funding_date = fields.DateField(null=True)
    facebook = fields.CharField(max_length=255, null=True)
    twitter = fields.CharField(max_length=255, null=True)
    youtube = fields.CharField(max_length=255, null=True)
    instagram = fields.CharField(max_length=255, null=True)
    annual_revenue = fields.CharField(max_length=255, null=True)

    class Meta:  # type: ignore
        table = "companies"