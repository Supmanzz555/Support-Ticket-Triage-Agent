"""FastAPI application and routes."""
import dataclasses
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    TicketThreadRequest,
    TriageResponse,
    ClassificationResponse,
    KBResultResponse,
    NextActionResponse,
)
from app.agent.triage_agent import triage_ticket
from app.agent.models import TicketThread, CustomerInfo, TicketMessage
from datetime import datetime

app = FastAPI(
    title="Support Ticket Triage Agent",
    description="AI agent for triaging customer support tickets",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Support Ticket Triage Agent API"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/triage", response_model=TriageResponse)
def triage_ticket_endpoint(request: TicketThreadRequest):
    """
    Triage a support ticket thread.
    
    Args:
        request: Ticket thread with customer info and messages
    
    Returns:
        Triage response with classification, KB results, and next action
    """
    try:
        # Convert request to internal models
        customer = CustomerInfo(
            plan=request.customer.plan,
            region=request.customer.region,
            tenure_months=request.customer.tenure_months,
            prior_tickets=request.customer.prior_tickets,
        )
        
        messages = [
            TicketMessage(
                timestamp=msg.timestamp,
                text=msg.text,
            )
            for msg in request.messages
        ]
        
        thread = TicketThread(customer=customer, messages=messages)
        
        # Run triage agent
        output = triage_ticket(thread)
        
        # Convert dataclasses to Pydantic response models
        return TriageResponse(
            classification=ClassificationResponse(**dataclasses.asdict(output.classification)),
            knowledge_base=[KBResultResponse(**dataclasses.asdict(r)) for r in output.kb_results],
            customer_profile=output.customer_profile,
            next_action=NextActionResponse(**dataclasses.asdict(output.next_action)),
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing ticket: {str(e)}")
