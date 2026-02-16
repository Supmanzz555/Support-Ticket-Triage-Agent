# Support Ticket Triage Agent

AI agent that triages support tickets: classifies urgency (critical/high/medium/low), extracts product/issue/sentiment, searches a RAG knowledge base, and decides next action (auto-respond, route to specialist, or escalate). Uses **2 tools**: KB search (Chroma vector DB) and customer profile lookup (mocked). No chat UI—terminal console or API only.

**Stack:** Python 3.11, FastAPI, OpenAI-compatible LLM (GPT/Groq), Chroma, Pydantic.

---

## Quick Start 



**Python:**
```bash
cp .env.reviewer .env   # set OPENAI_API_KEY=sk-...
pip install -r requirements.txt
python main.py
```

**Docker:**
```bash
docker build -t ticket-triage-agent .
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=sk-your-key ticket-triage-agent
```

Server: `http://localhost:8000`. KB auto-indexes on first run.

---

## Note for Reviewers

**Development setup:** During development, I used Groq (LLM) and Jina (embeddings) due to cost constraints. For Groq, I used `llama-3.1-8b-instant` as the base LLM model (via `groq/compound` system) because it supports tool calling and multilingual capabilities (handles Thai/English/etc.). However, the code is fully **OpenAI-compatible** set `OPENAI_API_KEY` and `EMBEDDING_PROVIDER=openai` (as shown in `.env.reviewer`) and it will work with OpenAI GPT models for both chat and embeddings. The code uses OpenAI-compatible APIs throughout.

---

## Test

**API:**
```bash
curl -X POST http://localhost:8000/triage -H "Content-Type: application/json" -d @data/tickets_sample.json
```

**Interactive chat:** `python chat_with_bot.py` — pick mock customer, chat with bot.

### Docker testing (Linux / macOS / Windows)

1. **Build image** (same command on all OS):
   ```bash
   docker build -t ticket-triage-agent .
   ```
2. **Run container with your API key**  
   - Linux / macOS (bash, zsh):
     ```bash
     docker run --rm -p 8000:8000 -e OPENAI_API_KEY=sk-your-key ticket-triage-agent
     ```
   - Windows (PowerShell):
     ```powershell
     docker run --rm -p 8000:8000 -e OPENAI_API_KEY=sk-your-key ticket-triage-agent
     ```
   - Or use a `.env` file on any OS:
     ```bash
     # .env contains OPENAI_API_KEY=sk-your-key
     docker run --rm -p 8000:8000 --env-file .env ticket-triage-agent
     ```
3. **Test inside Docker** – from your host:
   ```bash
   curl http://localhost:8000/health
   curl -X POST http://localhost:8000/triage \
     -H "Content-Type: application/json" \
     -d @data/tickets_sample.json
   ```

---

## Architecture & Design Decisions

- **Autonomous tool selection (OpenAI function calling)** — LLM chooses which tools to call instead of a fixed pipeline. Easier to add tools and adapt to context.
- **Single orchestration call** — One LLM call with tools; model gathers info then returns structured JSON. Fewer round-trips and lower cost.
- **Chroma for RAG** — Lightweight, file-backed, no extra server. Good fit for small KB and simple deployment.
- **Pydantic (API) + dataclasses (agent)** — Clear API contracts and validation; simple internal models.
- **KB manifest** — Reindex only when `data/kb/` files change; avoids redundant embedding work.
- **Language matching** — Bot responds in the same language as customer (Thai, English, etc.).

**Flow:** FastAPI → Agent → LLM (with tools) → Execute tools → LLM final decision → JSON response.

---

## Development Challenges & Mitigation

| Challenge | Mitigation |
|-----------|------------|
| **Groq rate limits** | Switched to `llama-3.1-8b-instant` (via `groq/compound`) for multilingual + tool calling; supports OpenAI fallback via env vars. |
| **Tool call validation** | Groq rejected `null` for optional `region` param. Updated tool schema: `"type": ["string", "null"]`. |
| **Chroma telemetry errors** |  harmless log (`capture() takes 1 positional argument`). Set `ANONYMIZED_TELEMETRY=False`; doesn't affect functionality. |
| **KB not reindexing** | Added manifest-based change detection; auto-reindexes when files added/edited. |
| **Missing auto-reply on route** | Added prompt instruction + fallback UX in chat script so customers always get acknowledgment. |
| **Language mismatch** | Added language matching instruction; bot responds in customer's language (Thai/English/etc.). |

## Production Considerations

**What could go wrong:**
- **LLM rate limits / API down** → Multiple providers (Groq/OpenAI) via env; add retries, backoff, fallback.
- **KB retrieval misses** → Hybrid search (semantic + keyword); monitor scores; improve KB from feedback.
- **Hallucination in auto-reply** → Ground replies in retrieved snippets; validate; route when unsure.
- **Tool failures** → Try/except; return errors to LLM; health checks; logging.
- **Inconsistent classification** → Lower temperature; log decisions; human review for critical/high.

**Evaluation metrics:**
- **Accuracy:** Compare urgency/product/sentiment to human labels; target >85% on urgency. Review routing (right queue) and auto-reply quality (human rating, CSAT).
- **Operations:** Latency (P95 <2s), cost per ticket, uptime.
- **Impact:** Escalation rate, first-contact resolution, time to first response.
- **Improvement:** A/B test prompts and KB; use "was this helpful?" and error analysis to refine.
- **Safety:** Audit log; always escalate disputes/legal/threats; check for bias by segment.

---

## Deliverables

| Item | Location |
|------|----------|
| **System prompt** | `app/agent/prompts.py` → `SYSTEM_PROMPT` |
| **Tool definitions** | `app/agent/prompts.py` → `TOOL_DEFINITIONS` |
| **Tool 1 – KB search** | `app/tools/knowledge_base.py` (Chroma RAG) |
| **Tool 2 – Customer profile** | `app/tools/customer_profile.py` (mocked) |

Sample tickets: `data/tickets_sample.json` (matches assignment PDF). KB: `data/kb/*.md` (7 docs).

---

## Project Structure

```
app/
  api.py, config.py, schemas.py, llm_client.py, vector_store.py, kb_loader.py
  agent/   models.py, prompts.py, triage_agent.py
  tools/   knowledge_base.py, customer_profile.py
data/      kb/*.md, tickets_sample.json, mock_customers.json
main.py, requirements.txt, Dockerfile, .env.example, .env.reviewer
```

---

## Configuration

- **for testing wtih your own api key:** `OPENAI_API_KEY` only; `EMBEDDING_PROVIDER=openai` in `.env.reviewer`.
- **Dev (Groq):** `GROQ_API_KEY`, `GROQ_MODEL=groq/compound`, `EMBEDDING_PROVIDER=jina`, `JINA_EMBEDDING_API_KEY`.

**Troubleshooting:** Missing KB → ensure `data/kb/` exists; reindex: `python -m app.kb_loader --force`. Reset Chroma: delete `chroma_db/`.
