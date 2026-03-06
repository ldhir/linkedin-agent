import json
import logging
import os
import sys
from datetime import datetime

import anthropic

from config import ORCHESTRATOR_MODEL
from prompts.system import build_system_prompt
from state import AgentContext, AgentState
from tools.draft import draft_linkedin_post
from tools.email_tool import check_for_reply, get_message_count, get_or_create_inbox, send_email
from tools.research import search_trending_topics

# Logging
os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs", "agent.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# Tool definitions for Claude
TOOLS = [
    {
        "name": "search_trending_topics",
        "description": "Search for trending LinkedIn topics from the last 3 days related to AI, sports tech, computer vision, edtech, consumer AI, startups, VC/fundraising.",
        "input_schema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional custom search queries. If not provided, uses defaults.",
                }
            },
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to the founder with topic options or a draft post.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["subject", "body"],
        },
    },
    {
        "name": "check_for_reply",
        "description": "Check if the founder has replied to the topic email.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "draft_linkedin_post",
        "description": "Draft a LinkedIn post given a topic and tone/vibe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The topic to write about"},
                "tone": {"type": "string", "description": "The tone/vibe (e.g., spicy hot take, thoughtful, storytelling)"},
                "context": {"type": "string", "description": "Additional research context about the topic"},
            },
            "required": ["topic", "tone"],
        },
    },
]


def execute_tool(name: str, inputs: dict, ctx: AgentContext) -> str:
    """Execute a tool call and return the result as a string."""
    log.info(f"Executing tool: {name} with inputs: {json.dumps(inputs)[:200]}")

    if name == "search_trending_topics":
        results = search_trending_topics(inputs.get("queries"))
        ctx.state = AgentState.EMAILING_TOPICS
        return json.dumps(results, indent=2)

    elif name == "send_email":
        # Ensure inbox exists
        if not ctx.inbox_id:
            ctx.inbox_id = get_or_create_inbox()

        result = send_email(inputs["subject"], inputs["body"], ctx.inbox_id)

        if ctx.state == AgentState.EMAILING_TOPICS:
            ctx.thread_subject = inputs["subject"]
            ctx.topics_email_body = inputs["body"]
            ctx.initial_message_count = get_message_count(ctx.inbox_id)
            ctx.state = AgentState.WAITING_FOR_REPLY
        elif ctx.state == AgentState.EMAILING_DRAFT:
            ctx.state = AgentState.DONE

        return json.dumps(result)

    elif name == "check_for_reply":
        if not ctx.inbox_id:
            return json.dumps({"error": "No inbox set up yet"})

        result = check_for_reply(ctx.inbox_id, ctx.initial_message_count)
        ctx.poll_count += 1
        ctx.last_poll_at = datetime.now().isoformat()

        if result["has_reply"]:
            ctx.state = AgentState.DRAFTING
        return json.dumps(result)

    elif name == "draft_linkedin_post":
        draft = draft_linkedin_post(
            inputs["topic"],
            inputs["tone"],
            inputs.get("context", ""),
        )
        ctx.draft = draft
        ctx.state = AgentState.EMAILING_DRAFT
        return draft

    return json.dumps({"error": f"Unknown tool: {name}"})


def build_user_message(ctx: AgentContext) -> str:
    """Build the initial user message based on current state."""
    today = datetime.now().strftime("%A, %B %d, %Y")

    if ctx.state == AgentState.IDLE:
        return f"Good morning! Today is {today}. Start by researching trending topics for a LinkedIn post."

    if ctx.state == AgentState.WAITING_FOR_REPLY:
        if ctx.poll_count >= ctx.max_polls:
            return "It's been too long without a reply. Send a 'skipping today' email and wrap up."
        return f"Check if the founder has replied. This is poll #{ctx.poll_count + 1}."

    if ctx.state == AgentState.DRAFTING:
        topics_context = f"\n\nOriginal topics email:\n{ctx.topics_email_body}" if ctx.topics_email_body else ""
        return f"The founder replied. Topic: {ctx.selected_topic}. Tone: {ctx.tone}. Draft the LinkedIn post.{topics_context}"

    if ctx.state == AgentState.EMAILING_DRAFT:
        return f"Send the draft to the founder. Here's the draft:\n\n{ctx.draft}"

    return f"Current state is {ctx.state.value}. Decide what to do next."


def run_agent():
    log.info("=" * 60)
    log.info("Agent invocation starting")

    ctx = AgentContext.load()
    log.info(f"Loaded state: {ctx.state.value}")

    # Reset if previous run is done and it's a new day
    if ctx.should_reset():
        log.info("New day detected, resetting state")
        ctx = AgentContext()

    # If already done today, exit
    if ctx.state == AgentState.DONE:
        log.info("Already done for today, exiting")
        return

    # Mark start time
    if not ctx.started_at:
        ctx.started_at = datetime.now().isoformat()

    # Timeout check
    if ctx.state == AgentState.WAITING_FOR_REPLY and ctx.poll_count >= ctx.max_polls:
        log.info("Max polls reached, sending timeout email")
        if not ctx.inbox_id:
            ctx.inbox_id = get_or_create_inbox()
        send_email(
            "Skipping today's LinkedIn post",
            "Hey! I didn't hear back from you today on topic selection, so I'm skipping today's post. I'll be back tomorrow morning with fresh topics!",
            ctx.inbox_id,
        )
        ctx.state = AgentState.DONE
        ctx.save()
        return

    # Build system prompt
    context_summary = f"State={ctx.state.value}, topics={len(ctx.topics)}, poll_count={ctx.poll_count}"
    if ctx.selected_topic:
        context_summary += f", selected_topic={ctx.selected_topic}"
    if ctx.tone:
        context_summary += f", tone={ctx.tone}"

    system = build_system_prompt(ctx.state.value, context_summary)
    messages = [{"role": "user", "content": build_user_message(ctx)}]

    client = anthropic.Anthropic()

    # Agent reasoning loop — max 10 iterations per invocation
    for iteration in range(10):
        log.info(f"Reasoning iteration {iteration + 1}")

        response = client.messages.create(
            model=ORCHESTRATOR_MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        log.info(f"Stop reason: {response.stop_reason}")

        # If Claude is done thinking, exit loop
        if response.stop_reason == "end_turn":
            # Log any text output
            for block in response.content:
                if hasattr(block, "text"):
                    log.info(f"Agent says: {block.text}")
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input, ctx)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

    ctx.save()
    log.info(f"Agent invocation complete. Final state: {ctx.state.value}")


if __name__ == "__main__":
    run_agent()
