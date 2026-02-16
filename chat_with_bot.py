#!/usr/bin/env python3
"""
Interactive terminal chat to test the RAG bot.

- Loads mock customer profiles from data/mock_customers.json (edit to simulate different user types).
- You pick a customer profile, then type messages as that customer.
- The bot triages each turn and answers using the knowledge base; you see classification, KB snippets, and the reply.

Usage:
  1. Ensure KB is indexed (run `python main.py` once, or the script will try to index on first run).
  2. Run: uv run python chat_with_bot.py
  3. Choose a customer profile by number.
  4. Type your message and press Enter; the bot responds. Type 'quit' or 'exit' to end.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent.models import CustomerInfo, TicketMessage, TicketThread
from app.agent.triage_agent import triage_ticket
from app.kb_loader import index_knowledge_base


MOCK_CUSTOMERS_PATH = Path(__file__).parent / "data" / "mock_customers.json"


def load_mock_customers():
    """Load customer profiles from data/mock_customers.json."""
    if not MOCK_CUSTOMERS_PATH.exists():
        print(f"Error: {MOCK_CUSTOMERS_PATH} not found. Create it from the template.")
        sys.exit(1)
    with open(MOCK_CUSTOMERS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("customers", data) if isinstance(data, dict) else data


def run_chat():
    customers = load_mock_customers()
    if not customers:
        print("No customers in mock_customers.json. Add at least one profile.")
        sys.exit(1)

    print("Mock customer profiles (edit data/mock_customers.json to add/change):")
    for i, c in enumerate(customers, 1):
        label = c.get("label", c.get("id", str(c)))
        print(f"  {i}. {label}")

    try:
        choice = input("\nSelect customer number (1–{}): ".format(len(customers)))
        idx = int(choice.strip()) - 1
        if idx < 0 or idx >= len(customers):
            print("Invalid number.")
            sys.exit(1)
    except (ValueError, EOFError):
        sys.exit(1)

    profile = customers[idx]
    customer = CustomerInfo(
        plan=profile["plan"],
        region=profile.get("region"),
        tenure_months=profile.get("tenure_months", 0),
        prior_tickets=profile.get("prior_tickets", 0),
    )
    messages: list[TicketMessage] = []

    print("\n--- Chat with RAG bot (customer: {} | plan: {}) ---".format(
        profile.get("label", profile.get("id", "")), customer.plan))
    print("Type your message and press Enter. The bot will triage and answer from the knowledge base.")
    print("Commands: quit, exit = end session\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        messages.append(TicketMessage(timestamp=datetime.utcnow(), text=user_input))
        thread = TicketThread(customer=customer, messages=messages)

        print("\nBot (thinking...)")
        try:
            output = triage_ticket(thread)
        except Exception as e:
            print(f"Error: {e}")
            continue

        print("\n--- Classification ---")
        print(f"  Urgency: {output.classification.urgency} | Issue: {output.classification.issue_type or '—'} | Sentiment: {output.classification.sentiment}")
        print(f"  Summary: {output.classification.short_summary}")

        if output.kb_results:
            print("\n--- Knowledge base used ---")
            for r in output.kb_results:
                print(f"  [{r.title}] (score: {r.score:.2f})")
                print(f"    {r.snippet[:200]}...")

        print("\n--- Next action ---")
        queue = output.next_action.target_queue
        if queue and str(queue).lower() != "null":
            print(f"  Action: {output.next_action.action} → {queue}")
        else:
            print(f"  Action: {output.next_action.action}")

        reply = output.next_action.auto_reply
        if reply and str(reply).strip().lower() != "null":
            print("\n--- Bot reply (to customer) ---")
            print(f"  {reply}")
        else:
            # Fallback UX: show a friendly acknowledgment when routing/escalating with no reply
            action = output.next_action.action
            queue = output.next_action.target_queue
            if action == "route_to_specialist" and queue and str(queue).lower() != "null":
                print("\n--- Bot reply (to customer) ---")
                print(f"  We're transferring your ticket to our {queue} team. A specialist will follow up shortly.")
            elif action == "escalate_to_human":
                print("\n--- Bot reply (to customer) ---")
                print("  We're escalating your ticket so a specialist can help. Someone will be in touch soon.")
            else:
                print("\n--- Bot reply (to customer) ---")
                print("  We're routing your ticket to the right team. A team member will follow up shortly.")

        print()


if __name__ == "__main__":
    print("Initializing knowledge base (if needed)...")
    index_knowledge_base()
    run_chat()
