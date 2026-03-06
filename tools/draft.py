import anthropic

from config import WRITER_MODEL
from prompts.post_drafting import WRITER_SYSTEM_PROMPT


def draft_linkedin_post(topic: str, tone: str, context: str = "", client: anthropic.Anthropic = None) -> str:
    if client is None:
        client = anthropic.Anthropic()

    response = client.messages.create(
        model=WRITER_MODEL,
        max_tokens=1024,
        system=WRITER_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Draft a LinkedIn post.

Topic: {topic}
Tone/vibe: {tone}
Additional context from research: {context}

Write the post ready to copy-paste. Nothing else.""",
        }],
    )
    return response.content[0].text
