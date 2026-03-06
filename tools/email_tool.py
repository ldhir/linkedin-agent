import os
import urllib.parse

import httpx
from agentmail import AgentMail
from agentmail.inboxes.types import CreateInboxRequest

INBOX_CLIENT_ID = "linkedin-agent-inbox-v1"
BASE_URL = "https://api.agentmail.to/v0"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('AGENTMAIL_API_KEY')}",
        "Content-Type": "application/json",
    }


def _encode_inbox(inbox_id: str) -> str:
    return urllib.parse.quote(inbox_id, safe="")


def get_client() -> AgentMail:
    return AgentMail(api_key=os.getenv("AGENTMAIL_API_KEY"))


def get_or_create_inbox() -> str:
    client = get_client()
    inbox = client.inboxes.create(
        request=CreateInboxRequest(
            display_name="LinkedIn Agent",
            client_id=INBOX_CLIENT_ID,
        )
    )
    return inbox.inbox_id


def send_email(subject: str, body: str, inbox_id: str) -> dict:
    to_address = os.getenv("FOUNDER_EMAIL")
    encoded = _encode_inbox(inbox_id)

    r = httpx.post(
        f"{BASE_URL}/inboxes/{encoded}/messages/send",
        headers=_headers(),
        json={
            "to": to_address,
            "subject": subject,
            "text": body,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {"status": "sent", "to": to_address, "subject": subject, "thread_id": data.get("thread_id")}


def check_for_reply(inbox_id: str, initial_message_count: int) -> dict:
    encoded = _encode_inbox(inbox_id)

    r = httpx.get(
        f"{BASE_URL}/inboxes/{encoded}/messages",
        headers=_headers(),
        params={"limit": 20},
        timeout=30,
    )
    r.raise_for_status()
    messages = r.json().get("messages", [])
    current_count = len(messages)

    if current_count <= initial_message_count:
        return {"has_reply": False}

    # Find the newest inbound message (from the founder, not from us)
    for msg in messages:
        from_addr = msg.get("from", "")
        if "agentmail.to" not in from_addr:
            # List endpoint doesn't include body — fetch the full message
            msg_id = urllib.parse.quote(msg.get("message_id", ""), safe="")
            r2 = httpx.get(
                f"{BASE_URL}/inboxes/{encoded}/messages/{msg_id}",
                headers=_headers(),
                timeout=30,
            )
            r2.raise_for_status()
            full_msg = r2.json()
            reply_text = full_msg.get("extracted_text") or full_msg.get("text") or ""
            return {
                "has_reply": True,
                "reply_body": reply_text,
                "message_count": current_count,
            }

    return {"has_reply": False}


def get_message_count(inbox_id: str) -> int:
    encoded = _encode_inbox(inbox_id)

    r = httpx.get(
        f"{BASE_URL}/inboxes/{encoded}/messages",
        headers=_headers(),
        params={"limit": 20},
        timeout=30,
    )
    r.raise_for_status()
    return len(r.json().get("messages", []))
