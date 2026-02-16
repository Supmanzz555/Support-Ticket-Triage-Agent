"""Pydantic schemas for FastAPI request/response models."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class CustomerInfoRequest(BaseModel):
    """Customer info in request."""
    plan: Literal["free", "pro", "enterprise"]
    region: Optional[str] = None
    tenure_months: int = Field(ge=0)
    prior_tickets: int = Field(ge=0, default=0)


class TicketMessageRequest(BaseModel):
    """Message in request."""
    timestamp: datetime
    text: str


class TicketThreadRequest(BaseModel):
    """Complete ticket thread request."""
    customer: CustomerInfoRequest
    messages: List[TicketMessageRequest]


class ClassificationResponse(BaseModel):
    """Classification in response."""
    urgency: Literal["critical", "high", "medium", "low"]
    product: Optional[str] = None
    issue_type: Optional[str] = None
    sentiment: Literal["very_negative", "negative", "neutral", "positive"]
    short_summary: str


class KBResultResponse(BaseModel):
    """KB result in response."""
    id: str
    title: str
    snippet: str
    score: float


class NextActionResponse(BaseModel):
    """Next action in response."""
    action: Literal["auto_respond", "route_to_specialist", "escalate_to_human"]
    target_queue: Optional[str] = None
    auto_reply: Optional[str] = None


class TriageResponse(BaseModel):
    """Complete triage response."""
    classification: ClassificationResponse
    knowledge_base: List[KBResultResponse]
    customer_profile: dict
    next_action: NextActionResponse
