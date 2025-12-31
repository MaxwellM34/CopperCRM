#!/usr/bin/env python3
import os
import requests

MAUTIC_BASE_URL = os.getenv("MAUTIC_BASE_URL", "http://138.197.156.191").rstrip("/")
MAUTIC_USERNAME = os.getenv("MAUTIC_USERNAME", "copper")
MAUTIC_PASSWORD = os.getenv("MAUTIC_PASSWORD", "copperisking67:)")
MAUTIC_COLD_SEGMENT_ID = os.getenv("MAUTIC_COLD_SEGMENT_ID", "10")  # This is the place where u switch segment

session = requests.Session()
session.auth = (MAUTIC_USERNAME, MAUTIC_PASSWORD)
session.headers.update({"Accept": "application/json"})


def _build_contact_payload(lead: dict, approval_status: str = "") -> dict:
    email = (lead.get("lead_email") or "").strip()
    name = (lead.get("lead_name") or "").strip()

    first_name = ""
    last_name = ""
    if name:
        parts = name.split(" ", 1)
        first_name = parts[0]
        if len(parts) > 1:
            last_name = parts[1]

    return {
        "email": email,
        "firstname": first_name,
        "lastname": last_name,
        "company": lead.get("company_name") or "",
        "website": lead.get("lead_website") or "",
        "position": lead.get("lead_title") or "",  
        "post_edit_email": lead.get("post_edit_email") or "",
        "email_2_approval": approval_status or (lead.get("approval_status") or ""),
        "overwriteWithBlank": "false",
    }


def _create_or_update_contact(payload: dict) -> int:
    """
    Create/update a contact in Mautic, return contact ID.
    """
    if not payload.get("email"):
        raise ValueError("lead_email is required to create a Mautic contact")

    url = f"{MAUTIC_BASE_URL}/api/contacts/new"

    resp = session.post(url, data=payload, timeout=10)
    if resp.status_code >= 400:
        # Log full body to understand why Mautic rejected the request.
        print(f"[Mautic] {resp.status_code} body: {resp.text}")
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["contact"]["id"]
    except (KeyError, TypeError):
        raise RuntimeError(f"Unexpected Mautic response: {data}")


def _add_to_segment(contact_id: int):
    """
    Add contact to the Cold Outbound segment.
    """
    url = f"{MAUTIC_BASE_URL}/api/segments/{MAUTIC_COLD_SEGMENT_ID}/contact/{contact_id}/add"
    resp = session.post(url, timeout=10)
    resp.raise_for_status()


def push_email_to_mautic(lead: dict, approval_status: str = "approved", add_to_segment: bool = True):
    """
    Main entrypoint: given an email row (dict), push to Mautic + add to segment.
    """
    if not lead.get("lead_email"):
        print(f"[Mautic] Skipping, no email for row id={lead.get('id')}")
        return

    # Only send post_edit_email.
    payload = _build_contact_payload(lead, approval_status=approval_status)

    print(f"[Mautic] Creating/updating contact for {lead['lead_email']}...")
    contact_id = _create_or_update_contact(payload)
    if add_to_segment:
        print(f"[Mautic] Contact ID: {contact_id}, adding to segment {MAUTIC_COLD_SEGMENT_ID}...")
        _add_to_segment(contact_id)
    print(f"[Mautic] Done for contact {contact_id}")


def push_approval_status_only(lead: dict, approval_status: str):
    """
    Update/contact create with approval status only (no segment add). Only sends post_edit_email.
    """
    if not lead.get("lead_email"):
        print(f"[Mautic] Skipping approval update, no email for row id={lead.get('id')}")
        return

    payload = _build_contact_payload(lead, approval_status=approval_status)
    print(f"[Mautic] Updating approval status for {lead['lead_email']} to {approval_status}...")
    _create_or_update_contact(payload)
    print("[Mautic] Approval status updated.")


def _find_contact_id_by_email(email: str) -> int:
    """
    Search for a contact ID by email. Returns -1 if not found.
    """
    if not email:
        return -1
    url = f"{MAUTIC_BASE_URL}/api/contacts"
    resp = session.get(url, params={"search": f"email:{email}"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # Mautic returns a dict of contacts keyed by ID
    try:
        contacts = data.get("contacts") or {}
        for cid in contacts:
            return int(cid)
    except Exception:
        pass
    return -1


def delete_contact_by_email(email: str) -> bool:
    """
    Delete a contact by email if found. Returns True on success or if not found.
    """
    cid = _find_contact_id_by_email(email)
    if cid < 0:
        print(f"[Mautic] Contact not found for email {email}; nothing to delete.")
        return True
    url = f"{MAUTIC_BASE_URL}/api/contacts/{cid}/delete"
    resp = session.post(url, timeout=10)
    if resp.status_code in (200, 404):
        print(f"[Mautic] Contact {cid} deleted (status {resp.status_code}).")
        return True
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f"[Mautic] Error deleting contact {cid}: {e}")
        return False
    return True
