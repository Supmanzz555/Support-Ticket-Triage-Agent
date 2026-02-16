"""Main triage agent operation"""
import json
from typing import Dict, Any, List
from app.agent.models import (
    TicketThread,
    Classification,
    NextAction,
    AgentOutput,
    KBResult,
)
from app.agent.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS
from app.llm_client import llm_client
from app.tools.knowledge_base import search_knowledge_base
from app.tools.customer_profile import get_customer_profile


def build_conversation_summary(thread: TicketThread) -> str:
    """text summary of the conversation"""
    lines = []
    for msg in thread.messages:
        lines.append(f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M')}] {msg.text}")
    return "\n".join(lines)


def execute_tool_call(tool_call: Dict[str, Any]) -> Any:
    """Execute a tool call and return the result"""
    function_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    if function_name == "search_knowledge_base":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 3)
        results = search_knowledge_base(query, top_k)
        # Convert KBResult objects to dicts for json encode
        return {
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "snippet": r.snippet,
                    "score": r.score,
                }
                for r in results
            ]
        }
    
    elif function_name == "get_customer_profile":
        customer_plan = arguments.get("customer_plan", "")
        tenure_months = arguments.get("tenure_months", 0)
        region = arguments.get("region")
        return get_customer_profile(customer_plan, tenure_months, region)
    
    else:
        return {"error": f"Unknown tool: {function_name}"}


def triage_ticket(thread: TicketThread) -> AgentOutput:
    """
    Main triage function - tools selection
    """
    #conversation summary
    conversation_summary = build_conversation_summary(thread)
    
    # user message with context
    user_message = f"""Customer Information:
- Plan: {thread.customer.plan}
- Region: {thread.customer.region or 'Not specified'}
- Tenure: {thread.customer.tenure_months} months
- Prior tickets: {thread.customer.prior_tickets}

Conversation:
{conversation_summary}

Please analyze this ticket, use the available tools to gather information, and provide your triage decision."""
    
    # Initialize conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    
    # Track tool calls and results
    tool_results = []
    kb_results = []
    customer_profile = None
    max_iterations = 10
    iteration = 0
    
    # Main agent loop
    while iteration < max_iterations:
        iteration += 1
        
        # LLM call with tools
        response = llm_client.chat_completion(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        
        # Add assistant message
        assistant_message = {"role": "assistant", "content": response["content"]}
        if response["tool_calls"]:
            assistant_message["tool_calls"] = response["tool_calls"]
        messages.append(assistant_message)
        
        # if no call
        if not response["tool_calls"]:
            break
        
        # Execute tool calls
        for tool_call in response["tool_calls"]:
            tool_result = execute_tool_call(tool_call)
            tool_results.append({
                "tool_call_id": tool_call["id"],
                "name": tool_call["function"]["name"],
                "result": tool_result,
            })
            
            # tools results if calleds
            if tool_call["function"]["name"] == "search_knowledge_base":
                kb_results = [
                    KBResult(**r) for r in tool_result.get("results", [])
                ]
            elif tool_call["function"]["name"] == "get_customer_profile":
                customer_profile = tool_result
        
        # add tool result to chat
        for tool_result in tool_results[-len(response["tool_calls"]):]:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_call_id"],
                "name": tool_result["name"],
                "content": json.dumps(tool_result["result"]),
            })
    
    # sturcture output
    final_prompt = """Based on your analysis and the tool results, provide your final triage decision in JSON format:

{
  "classification": {
    "urgency": "critical|high|medium|low",
    "product": "product name or null",
    "issue_type": "issue type or null",
    "sentiment": "very_negative|negative|neutral|positive",
    "short_summary": "one sentence summary"
  },
  "next_action": {
    "action": "auto_respond|route_to_specialist|escalate_to_human",
    "target_queue": "billing|infra|product|general_support|null",
    "auto_reply": "reply text if auto_respond, otherwise null"
  }
}"""
    
    messages.append({"role": "user", "content": final_prompt})
    
    final_response = llm_client.chat_completion(
        messages=messages,
        response_format={"type": "json_object"},
    )
    
    # Parse final JSON output
    try:
        decision = json.loads(final_response["content"])
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        decision = {
            "classification": {
                "urgency": "medium",
                "product": None,
                "issue_type": None,
                "sentiment": "neutral",
                "short_summary": "Unable to parse response",
            },
            "next_action": {
                "action": "escalate_to_human",
                "target_queue": None,
                "auto_reply": None,
            },
        }
    
    # Build output objects (normalize LLM "null" strings to None)
    classification = Classification(**decision["classification"])
    na = decision["next_action"]
    if na.get("auto_reply") in (None, "null") or str(na.get("auto_reply", "")).strip().lower() == "null":
        na["auto_reply"] = None
    if na.get("target_queue") in (None, "null") or str(na.get("target_queue", "")).strip().lower() == "null":
        na["target_queue"] = None
    next_action = NextAction(**na)
    
    # make sure customer profile was retrieved
    if customer_profile is None:
        customer_profile = get_customer_profile(
            thread.customer.plan,
            thread.customer.tenure_months,
            thread.customer.region,
        )
    
    return AgentOutput(
        classification=classification,
        kb_results=kb_results,
        customer_profile=customer_profile,
        next_action=next_action,
    )
