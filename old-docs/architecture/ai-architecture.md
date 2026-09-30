# AI Architecture — Health Tracker

## Overview

Four AI subsystems working together:

```
┌─────────────────────────────────────────────────┐
│                   AI MODULE                       │
│                                                   │
│  ┌───────────┐  ┌────────┐  ┌─────────────────┐ │
│  │ LLM Layer │  │  RAG   │  │    Agents       │ │
│  │ 3 providers│  │Pipeline│  │ ReAct + 5 tools │ │
│  │ (Strategy) │  │pgvector│  │ + memory        │ │
│  └─────┬─────┘  └───┬────┘  └────────┬────────┘ │
│        │             │                │           │
│        └─────────────┼────────────────┘           │
│                      │                            │
│              ┌───────▼───────┐                    │
│              │   Workflows   │                    │
│              │ Multi-step    │                    │
│              │ orchestrated  │                    │
│              └───────────────┘                    │
└─────────────────────────────────────────────────┘
```

## 1. LLM Layer — Provider Abstraction

**Pattern:** Strategy + Factory

```python
BaseLLMClient (ABC)        # Interface: chat(), stream_chat(), embed()
├── OllamaClient           # Free, local (localhost:11434)
├── GroqClient             # Free, cloud (api.groq.com)
└── OpenAIClient           # Paid, production (api.openai.com)

get_llm_client() → BaseLLMClient  # Factory returns based on LLM_PROVIDER config
```

**Why this pattern:** Change `LLM_PROVIDER=groq` in .env → entire app uses Groq. Zero code changes. This is how production systems handle multi-vendor AI.

## 2. RAG Pipeline — Document Q&A

**Ingestion** (upload time):
```
PDF Upload → Extract Text (PyPDF2) → Chunk (recursive, 500 tokens, 50 overlap)
→ Embed (nomic-embed-text, 768 dims) → Store in pgvector
```

**Retrieval** (query time):
```
User Question → Embed Question → Cosine Similarity Search (pgvector <=>)
→ Top 5 Chunks (above 0.3 threshold) → Token Budget Filter (max 2000)
→ Format with Citations → Inject into LLM Prompt → Answer with Sources
```

**Key decisions:**
- pgvector over Pinecone: free, same database, transactional with document records
- IVFFlat index: ~95% recall, 10-100x faster than brute force scan
- 768 dimensions: nomic-embed-text (free via Ollama), 1536 for OpenAI
- Chunk overlap 50 tokens: preserves context at boundaries

## 3. ReAct Agent — Tool-Calling Health Coach

**The Loop:**
```
User: "Why am I tired this week?"

THINK 1 → "Check sleep data"
ACT 1   → query_logs(habit="Sleep", days=7) → "Avg 5.2 hrs"
THINK 2 → "Check correlation with energy"
ACT 2   → correlate_habits(a="Sleep", b="Mood") → "r=0.72 (strong positive)"
THINK 3 → "Search documents for fatigue"
ACT 3   → search_documents(query="fatigue causes") → "[Source: nutrition.pdf]..."
ANSWER  → "Your average sleep was 5.2 hours this week, well below the 7-8 hour
           recommendation. There's a strong correlation (0.72) between your sleep
           and mood scores. Your nutrition guide mentions iron deficiency as a
           fatigue factor [Source: nutrition.pdf, p.12]."
```

**5 Tools:**

| Tool | What It Does | When Used |
|------|-------------|-----------|
| `query_logs` | Fetch habit data by name + date range | "How much water this week?" |
| `get_analytics` | Streaks, weekly summary, completion rates | "How are my streaks?" |
| `search_documents` | RAG vector search on uploaded docs | "What does my blood report say?" |
| `correlate_habits` | Pearson correlation between two habits | "Does sleep affect mood?" |
| `create_plan` | Generate structured improvement plan | "Help me sleep better" |

**Memory:**
- Short-term: sliding window of last 20 messages (in-memory, per session)
- Long-term: key insights in Redis hash (persistent, across sessions)
  - "dietary_preference": "vegetarian"
  - "health_goal": "improve sleep to 8 hours"

## 4. Agentic Workflow — Weekly Report Pipeline

**Pattern:** Multi-step pipeline with orchestrator

```
Step 1: DataCollector
  → Query all habit logs, streaks, weekly comparison, completion rates
  → Format as structured text summary
  → Output: data_summary (string)

Step 2: Analyzer (LLM)
  → Input: data_summary
  → Prompt: "Find top 3 improvements, concerning trends, correlations"
  → Output: analysis (markdown)

Step 3: ReportWriter (LLM)
  → Input: data_summary + analysis
  → Prompt: "Write a friendly, personalized weekly report"
  → Output: report (markdown)

Orchestrator manages:
  - Step sequencing (1 → 2 → 3)
  - Retry on failure (max 2 retries)
  - Graceful degradation (partial report if step 2 fails)
  - Logging (timing, tokens, success/failure per step)
```

## 5. Cost Analysis (Free Tier)

| Component | Development | Staging | Production |
|-----------|------------|---------|------------|
| LLM (chat) | Ollama ($0) | Groq ($0) | OpenAI (~$0.50/user/month) |
| Embeddings | Ollama ($0) | Ollama ($0) | OpenAI (~$0.10/user/month) |
| Vector DB | pgvector ($0) | Supabase ($0) | RDS (included in DB cost) |
| Total AI cost | **$0** | **$0** | **~$0.60/user/month** |
