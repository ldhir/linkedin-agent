import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AGENTMAIL_API_KEY = os.getenv("AGENTMAIL_API_KEY")
FOUNDER_EMAIL = os.getenv("FOUNDER_EMAIL")

ORCHESTRATOR_MODEL = "claude-sonnet-4-20250514"
WRITER_MODEL = "claude-sonnet-4-20250514"

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))
MAX_POLLS = int(os.getenv("MAX_POLLS", "60"))
