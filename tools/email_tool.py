import urllib.parse

import httpx
from agentmail import AgentMail
from agentmail.inboxes.types import CreateInboxRequest

from config import AGENTMAIL_API_KEY, FOUNDER_EMAIL

INBOX_CLIENT_ID = "linkedin-agent-inbox-v1"
BASE_URL = "https://api.agentmail.to/v0"
REQUEST_TIMEOUT = 30


def _request(method: str, path: str, **kwargs) -> dict:
    r = httpx.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {AGENTMAIL_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )
    r.raise_for_status()
    return r.json()


def _encode_inbox(inbox_id: str) -> str:
    return urllib.parse.quote(inbox_id, safe="")


def get_or_create_inbox() -> str:
    client = AgentMail(api_key=AGENTMAIL_API_KEY)
    inbox = client.inboxes.create(
        request=CreateInboxRequest(
            display_name="LinkedIn Agent",
            client_id=INBOX_CLIENT_ID,
        )
    )
    return inbox.inbox_id


def send_email(subject: str, body: str, inbox_id: str) -> dict:
    encoded = _encode_inbox(inbox_id)
    data = _request("POST", f"/inboxes/{encoded}/messages/send", json={
        "to": FOUNDER_EMAIL,
        "subject": subject,
        "text": body,
    })
    return {"status": "sent", "to": FOUNDER_EMAIL, "subject": subject, "thread_id": data.get("thread_id")}


def check_for_reply(inbox_id: str, initial_message_count: int) -> dict:
    encoded = _encode_inbox(inbox_id)
    messages = _request("GET", f"/inboxes/{encoded}/messages", params={"limit": 20}).get("messages", [])
    current_count = len(messages)

    if current_count <= initial_message_count:
        return {"has_reply": False}

    # Find the newest inbound message (from the founder, not from us)
    for msg in messages:
        from_addr = msg.get("from", "")
        if "agentmail.to" not in from_addr:
            msg_id = urllib.parse.quote(msg.get("message_id", ""), safe="")
            full_msg = _request("GET", f"/inboxes/{encoded}/messages/{msg_id}")
            reply_text = full_msg.get("extracted_text") or full_msg.get("text") or ""
            return {
                "has_reply": True,
                "reply_body": reply_text,
                "message_count": current_count,
            }

    return {"has_reply": False}


def get_message_count(inbox_id: str) -> int:
    encoded = _encode_inbox(inbox_id)
    return len(_request("GET", f"/inboxes/{encoded}/messages", params={"limit": 20}).get("messages", []))
