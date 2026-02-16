
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Literal


@dataclass
class CustomerInfo:
    """Customer info"""
    plan: str  # "free", "pro", "enterprise"
    region: Optional[str] = None
    tenure_months: int = 0
    prior_tickets: int = 0


@dataclass
class TicketMessage:
    """Single message in a ticket chat"""
    timestamp: datetime
    text: str


@dataclass
class TicketThread:
    """full ticket messages that include customer info"""
    customer: CustomerInfo
    messages: List[TicketMessage]


@dataclass
class Classification:
    """classification results from llm"""
    urgency: Literal["critical", "high", "medium", "low"]
    product: Optional[str] = None
    issue_type: Optional[str] = None
    sentiment: Literal["very_negative", "negative", "neutral", "positive"] = "neutral"
    short_summary: str = ""


@dataclass
class KBResult:
    """Knowledge base search result."""
    id: str
    title: str
    snippet: str
    score: float


@dataclass
class NextAction:
    """Next action decision"""
    action: Literal["auto_respond", "route_to_specialist", "escalate_to_human"]
    target_queue: Optional[str] = None  # "billing", "infra", "product", etc.
    auto_reply: Optional[str] = None


@dataclass
class AgentOutput:
    """Complete agent output"""
    classification: Classification
    kb_results: List[KBResult]
    customer_profile: dict
    next_action: NextAction
