from __future__ import annotations
from typing import Dict, List

from segment_detector import detect_segment, detect_persona


def build_valueprop_prompt(lead: Dict[str, str], email_text: str) -> str:
    """
    Build the LLM prompt for value-prop fit, using ONLY fields that actually
    exist on imported_leads.

    lead keys (exact): id, canonical_email, work_email, personal_email,
    first_name, last_name, job_title, company, work_email_status,
    work_email_quality, work_email_confidence, primary_work_email_source,
    work_email_service_provider, catch_all_status, person_address, country,
    seniority, departments, personal_linkedin, profile_summary,
    company_linkedin, industries, company_summary, company_keywords, website,
    num_employees, phone, company_address, company_city, company_state,
    company_country, company_phone, company_email, technologies, latest_funding,
    latest_funding_amount, last_raised_at, facebook, twitter, youtube,
    instagram, annual_revenue, created_at, updated_at.
    """

    # Use our cleaned segment + persona logic
    segments: List[str] = detect_segment(lead)
    persona: str = detect_persona(lead)

    # Explicit, high-signal fields first
    header_lines = [
        f"Name: {lead.get('first_name','')} {lead.get('last_name','')}",
        f"Title: {lead.get('job_title','')}",
        f"Company: {lead.get('company','')}",
        f"Industry: {lead.get('industries','')}",
        f"Country: {lead.get('country','')}",
        f"Seniority: {lead.get('seniority','')}",
        f"Departments: {lead.get('departments','')}",
        f"Company size (# employees): {lead.get('num_employees','')}",
        f"Annual revenue: {lead.get('annual_revenue','')}",
        f"Website: {lead.get('website','')}",
        f"Technologies: {lead.get('technologies','')}",
    ]

    # Add a few extra useful fields if present
    extra_lines = []
    for key in [
        "work_email_status",
        "work_email_quality",
        "work_email_confidence",
        "company_summary",
        "company_keywords",
        "profile_summary",
        "latest_funding",
        "latest_funding_amount",
        "last_raised_at",
    ]:
        value = lead.get(key)
        if value:
            extra_lines.append(f"{key}: {value}")

    lead_context = "\n".join(header_lines + [""] + extra_lines)

    prompt = f"""
You are evaluating a cold outbound email for VALUE-PROPOSITION FIT ONLY.

You are NOT judging grammar, formatting, or deliverability. Focus only on:
- how strong and specific the value proposition is for THIS lead
- whether the benefits, problems, and outcomes match their segment and persona
- whether the message uses an appropriate angle and level of detail for this recipient

As part of your reasoning, you must:
- infer what value propositions the email is actually offering (in your own words)
- compare those implied benefits against what this segment and persona realistically care about
- heavily penalise generic, one-size-fits-all pitches that could be sent to anyone

Lead Information (from our CRM / vendor data):
{lead_context}

Detected Segment(s): {segments}
Detected Persona: {persona}

Email Body (no subject line):
\"\"\"{email_text.strip()}\"\"\"


Scoring rules (value proposition fit, 1–7 or "none"):

- You are scoring only how well the email's value proposition fits THIS lead in THIS context.
- Return a DISCRETE INTEGER score from 1 to 7, where 7 is the highest possible value-proposition fit.
- If the email is so bad or off-target that it should not be used at all, return the special score "none" instead of a number.

Score 7 (excellent fit):
- Very strong, specific, and compelling value proposition for THIS lead and segment.
- Clearly tied to the lead's role, organization, or industry.
- Clearly states or strongly implies concrete outcomes (e.g., faster decisions, reduced lab load, better compliance visibility, lower operational risk).
- The angle and level of technical detail are appropriate for the persona:
  - Executives: outcomes, risk, cost, compliance, strategic benefits.
  - Operations: workflow, reliability, speed, ease of use, alarms/alerts.
  - Technical: data quality, validation, methods, sensitivity/specificity, technical advantages.
- It feels like this value proposition was written specifically for this type of recipient.

Scores 5–6 (good but with issues):
- Generally appropriate for the segment and persona, but with at least one flaw (too generic, missing a key driver, wrong emphasis, or too vague).

Scores 3–4 (weak fit):
- Value proposition is present but only loosely connected to this lead's context.
- Mostly generic language that could apply to almost any B2B contact.
- Important drivers for this industry/persona are ignored or hand-wavy.

Scores 1–2 (very poor fit):
- Mostly misaligned with the lead's role, industry, or environment.
- Focuses on benefits that are clearly not relevant or uses an obviously wrong angle.

Score "none" (unusable):
- The email's value proposition is incoherent, self-contradictory, or completely off-target.
- Or the claims are so unrealistic or misleading that the message should not be used at all.

Additional rules for generic / AI-like value props:
- If the value proposition is extremely generic (could obviously be sent to any random B2B contact), the score MUST be 4 or lower.
- If the pitch feels like buzzword soup without clear, concrete outcomes, the score should usually be 3 or lower.
- If the email makes strong claims that contradict the segment or persona, treat this as very poor fit (1–2 or "none").

Feedback rules:
- If the score is 7, feedback must be an empty string "".
- If the score is less than 7, feedback must be ONE short sentence (max ~25 words) describing the single biggest issue, in very concrete terms.
- Feedback must start with 'Biggest issue:' and should reference the segment or persona where possible.

Respond ONLY with a JSON object of the form:
{{
  "score": 7,          // or 1–6, or "none"
  "feedback": ""       // empty string if score == 7, otherwise ONE specific sentence of feedback starting with 'Biggest issue:'
}}
"""
    return prompt.strip()
