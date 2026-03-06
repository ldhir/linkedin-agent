# LinkedIn Content Agent

An autonomous AI agent that researches trending topics and drafts LinkedIn posts for you every morning — all through email.

Built for founders who want to build a LinkedIn presence without spending hours on content. The agent does the research, you pick the angle.

## How It Works

```
7:00 AM  →  Agent researches trending topics (Tavily)
         →  Claude picks the 5 most relevant to your space
         →  Sends you an email with topic options + asks for tone

You reply →  "Do #3, spicy hot take"

Agent    →  Reads your reply
         →  Drafts a LinkedIn post with your brand voice (Claude)
         →  Emails you the final post to copy-paste
```

This is a **true agent**, not a script. It uses a Claude-powered reasoning loop with tool use, a persistent state machine, and makes autonomous decisions about topic relevance, email composition, and post drafting.

## Architecture

```
State Machine:  IDLE → RESEARCHING → EMAILING_TOPICS → WAITING_FOR_REPLY → DRAFTING → EMAILING_DRAFT → DONE
                                                              ↑ (polls every 5 min via cron)
```

- **Orchestrator**: Claude with tool use drives the entire loop — decides what action to take based on current state
- **Writer**: Separate Claude call with a dedicated brand-voice system prompt for high-quality post drafting
- **State**: JSON file persistence between cron invocations — idempotent and resilient to restarts
- **Research**: Tavily API searches trending topics + what successful founders are posting
- **Email**: AgentMail API for sending and receiving emails (two-way conversation)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourusername/linkedin-agent.git
cd linkedin-agent
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Get API keys

| Service | What it does | Get it at |
|---------|-------------|-----------|
| Anthropic | Claude for reasoning + writing | [console.anthropic.com](https://console.anthropic.com) |
| Tavily | Trending topic research | [app.tavily.com](https://app.tavily.com) (free tier: 1000 searches/mo) |
| AgentMail | Send/receive emails | [agentmail.to](https://agentmail.to) |

### 3. Configure

```bash
cp .env.example .env
# Fill in your API keys and email
```

### 4. Test it

```bash
.venv/bin/python3 agent.py
```

This will research topics, email you options, and wait for your reply. Run it again after replying to get your draft.

### 5. Set up cron (optional)

```bash
crontab -e
```

```cron
# Morning kickoff at 7 AM
0 7 * * * cd /path/to/linkedin-agent && .venv/bin/python3 agent.py >> logs/agent.log 2>&1

# Poll for reply every 5 min, 7 AM - noon
*/5 7-11 * * * cd /path/to/linkedin-agent && .venv/bin/python3 agent.py >> logs/agent.log 2>&1
```

## Project Structure

```
├── agent.py            # Main entry — Claude reasoning loop with tool use
├── state.py            # State machine + JSON persistence
├── config.py           # Environment config
├── tools/
│   ├── research.py     # Tavily API — trending topic search
│   ├── email_tool.py   # AgentMail — send/receive emails
│   └── draft.py        # Claude writer with brand voice prompt
├── prompts/
│   ├── system.py       # Orchestrator system prompt
│   └── post_drafting.py# Writer system prompt
├── requirements.txt
└── .env.example
```

## Customization

**Change the brand voice**: Edit `prompts/post_drafting.py` — the `WRITER_SYSTEM_PROMPT` controls how posts are written.

**Change research topics**: Edit `DEFAULT_QUERIES` in `tools/research.py` — add or modify search queries to match your space.

**Change the orchestrator behavior**: Edit `prompts/system.py` — this controls how the agent picks topics, writes emails, and makes decisions.

## Built With

- [Claude](https://anthropic.com) — reasoning + content generation
- [Tavily](https://tavily.com) — AI-native search API
- [AgentMail](https://agentmail.to) — email API for agents
