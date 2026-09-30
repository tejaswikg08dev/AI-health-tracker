# 🤖 Phase 4 Part 12d: AI — Complete Architecture

> **"39 files, 4 layers, 9 endpoints. The AI module is the largest and most complex in the project. This doc maps every file and every connection."**

---

## 1. Complete AI Module File Map (39 Files)

```
backend/app/modules/ai/
├── models.py          ← 4 SQLAlchemy models (Part 12a)
├── schemas.py         ← Request/response schemas (Part 12a)
├── service.py         ← Orchestration layer (Part 12b)
├── router.py          ← 9 endpoints + SSE streaming (Part 12b)
│
├── llm/               ← LLM LAYER (Part 08) — 8 files
│   ├── base_client.py       ← Abstract interface (Strategy pattern)
│   ├── ollama_client.py     ← Ollama provider (free, local)
│   ├── groq_client.py       ← Groq provider (free, cloud)
│   ├── openai_client.py     ← OpenAI provider (paid, production)
│   ├── factory.py           ← get_llm_client() factory
│   ├── prompt_templates.py  ← Jinja2 prompt templates
│   └── token_tracker.py     ← Token usage tracking
│
├── rag/               ← RAG LAYER (Part 09) — 5 files
│   ├── document_processor.py  ← PDF/TXT text extraction
│   ├── chunker.py             ← Recursive text splitting
│   ├── embeddings.py          ← Text → vector via LLM
│   ├── vector_store.py        ← pgvector store + search
│   └── retriever.py           ← Full retrieval pipeline
│
├── agents/            ← AGENTS LAYER (Part 10) — 10 files
│   ├── base_agent.py         ← ★★★ ReAct loop
│   ├── health_coach.py       ← Pre-configured health agent
│   ├── tools/
│   │   ├── base_tool.py      ← Abstract tool interface
│   │   ├── query_logs.py     ← Fetch habit data
│   │   ├── get_analytics.py  ← Get analytics
│   │   ├── correlate.py      ← Find correlations
│   │   ├── search_docs.py    ← RAG vector search
│   │   └── create_plan.py    ← Generate action plan
│   └── memory/
│       ├── short_term.py     ← Conversation buffer (20 msgs)
│       └── long_term.py      ← Persistent insights (Redis)
│
└── workflows/         ← WORKFLOWS LAYER (Part 11) — 5 files
    ├── base_workflow.py      ← Abstract workflow + state
    ├── orchestrator.py       ← Run + checkpoint + retry
    └── weekly_report/
        ├── data_collector.py ← Step 1: fetch data
        ├── analyzer.py       ← Step 2: LLM analysis
        └── report_writer.py  ← Step 3: LLM report writing
```

---

## 2. Complete AI Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI MODULE (39 files)                          │
│                                                                      │
│  router.py ──────────────────────────────────────────────────────── │
│    POST /chat ──→ service.chat() ──→ HealthCoachAgent.run()         │
│    GET /chat/stream ──→ service.stream_chat() ──→ SSE via LLM      │
│    POST /documents ──→ service.upload_document() ──→ RAG ingestion  │
│    POST /weekly-report ──→ service.generate_report() ──→ Workflow   │
│                                                                      │
│  service.py (orchestrator) ─────────────────────────────────────── │
│    │         │          │          │                                 │
│    ▼         ▼          ▼          ▼                                 │
│  AGENTS    RAG       LLM       WORKFLOWS                            │
│  ReAct     Embed     Chat      Weekly Report                        │
│  5 tools   Search    Stream    4 steps                              │
│  Memory    Format    Embed     Checkpoint                           │
│    │         │          │          │                                 │
│    └─────────┴──────────┴──────────┘                                │
│                    │                                                 │
│                    ▼                                                 │
│    ┌──────────────────────────────────┐                             │
│    │  External: Ollama/Groq/OpenAI    │                             │
│    │  Internal: PostgreSQL + pgvector  │                             │
│    │  Internal: Redis (memory + cache) │                             │
│    └──────────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. AI Module — By the Numbers

| Metric | Value |
|--------|-------|
| **Total files** | 39 |
| **Endpoints** | 9 |
| **Database tables** | 4 (documents, chunks, messages, insights) |
| **LLM providers** | 3 (Ollama, Groq, OpenAI) |
| **Agent tools** | 5 |
| **Memory types** | 2 (short-term + long-term) |
| **RAG pipeline steps** | 4 (extract → chunk → embed → store) |
| **Workflow steps** | 3 (collect → analyze → write) |
| **Design patterns** | Strategy, Factory, Abstract Base, ReAct, Pipeline |

---

## 4. Interview Summary: Complete AI Module

**Q: Walk me through your AI module architecture.**

**A:** "Four layers. The **LLM layer** uses the Strategy pattern — an abstract `BaseLLMClient` with three implementations (Ollama for free local dev, Groq for free cloud, OpenAI for production). A factory function returns the right one from config. The **RAG layer** handles document upload: extract text from PDFs, split into overlapping chunks, embed into 768-dim vectors via the LLM, and store in PostgreSQL's pgvector. On query, we embed the question, cosine-search pgvector, and format results with source citations. The **Agents layer** implements a ReAct loop: the LLM thinks about what to do, calls one of 5 tools (query logs, analytics, correlations, doc search, plan generation), observes the result, and iterates up to 5 times. Memory is two-tier: short-term conversation buffer and long-term Redis-based insights. The **Workflows layer** orchestrates multi-step AI tasks like the weekly report: gather data, LLM analyzes patterns, LLM writes a friendly report, save to database. All 39 files are built from scratch — no LangChain — to understand every layer from first principles."

---

| ⬅️ Previous | [Part 12c: AI Migration](./phase4-part12c-ai-migration.md) |
| ➡️ Next | [Part 13: Notifications Module Overview](./phase4-part13-notifications-module-overview.md) |

**🎉 THE AI MODULE IS COMPLETE.** 39 files, 4 layers, built from scratch. Next: Notifications, Export, Lambda, Frontend.
