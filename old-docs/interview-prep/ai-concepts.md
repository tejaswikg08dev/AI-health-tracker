# AI Concepts — Explained in Your Own Words

Write your own understanding here after building the project. This becomes your interview study sheet.

---

## LLM (Large Language Model)

**What it is:** _A neural network trained on massive text data that predicts the next token (word/piece of word). It doesn't "understand" — it generates statistically likely text based on the input._

**How you used it:** _Three providers (Ollama local, Groq cloud, OpenAI production) behind a Strategy pattern. Same interface, different backends. Chat endpoint sends conversation history + system prompt → gets text response._

**Key terms to know:**
- Token: ~4 characters of text. LLMs think in tokens, not words
- Temperature: 0.0 = deterministic, 1.0 = creative/random
- Context window: max tokens the model can process (4K-128K)
- System prompt: instructions that define the AI's behavior

---

## RAG (Retrieval-Augmented Generation)

**What it is:** _Instead of the LLM answering from memory (which can be wrong), we RETRIEVE real information from the user's documents and AUGMENT the prompt with it. The LLM then GENERATES an answer using that real context._

**How you built it:**
1. Ingestion: PDF → extract text → chunk (500 tokens, 50 overlap) → embed → pgvector
2. Retrieval: question → embed → cosine similarity search → top 5 chunks → inject into prompt
3. Generation: LLM answers using the retrieved context + cites sources

**Why chunking:** LLMs have token limits. Can't fit a 50-page PDF. Chunks = precise retrieval.

**Why overlap:** "The patient's iron level is | 10.5 which is low" — without overlap, neither chunk has the full sentence.

**Why pgvector (not Pinecone):** Free, same database, transactional, good enough < 1M vectors.

---

## AI Agents (ReAct Pattern)

**What it is:** _An LLM that can REASON about what to do and ACT by calling tools. Regular chatbot = one LLM call. Agent = multiple LLM calls with tool use between them._

**The ReAct loop you built:**
```
User: "Why am I tired?"
THINK: "I need sleep data" → ACT: query_logs("Sleep", 7 days) → OBSERVE: "avg 5.2 hrs"
THINK: "Check correlation" → ACT: correlate("Sleep", "Mood") → OBSERVE: "r=0.72"
THINK: "I have enough info" → ANSWER: "Your sleep averaged 5.2 hours..."
```

**Your tools:** query_logs, get_analytics, search_documents (RAG), correlate_habits, create_plan

**Memory:**
- Short-term: conversation buffer (last 20 messages) — for follow-up questions
- Long-term: Redis hash (persistent) — "user is vegetarian", survives across sessions

---

## Agentic Workflows

**What it is:** _Multiple agents/steps working in a pipeline. Each agent specializes in one task. Data flows from one to the next._

**Your weekly report pipeline:**
```
DataCollector → gathers all habit data for the week (Python, no LLM)
    ↓ data_summary
Analyzer → finds patterns, insights (LLM call with analysis prompt)
    ↓ analysis
ReportWriter → writes personalized friendly report (LLM call with writer prompt)
    ↓ report
```

**Why 3 steps (not 1):** One LLM doing everything produces mediocre results. Specialized prompts for analysis vs writing produce better output. Same principle as microservices — separation of concerns.

**Orchestrator handles:** step sequencing, retry on failure (max 2), graceful degradation (partial report if step 2 fails), timing/token logging.

---

## How to Explain in Interviews

**"What's the difference between a chatbot and an AI agent?"**
> A chatbot is a single LLM call — question in, answer out. An agent is a loop: the LLM reasons, decides to call tools (database queries, document search), observes the results, and repeats until it has enough information to answer. My health coach agent has 5 tools and can make up to 5 tool calls per question.

**"How does RAG work?"**
> Instead of trusting the LLM's memory, we retrieve real information from the user's documents. Upload: PDF → extract text → chunk into 500-token pieces → embed into vectors → store in pgvector. Query: embed the question → cosine similarity search for top 5 chunks → inject into the prompt with source citations → LLM answers using that real context.

**"How do you handle different LLM providers?"**
> Strategy pattern. Abstract BaseLLMClient with chat(), stream_chat(), embed() methods. Three implementations: Ollama (free local), Groq (free cloud), OpenAI (paid production). A factory function reads LLM_PROVIDER from environment and returns the right one. The rest of the app doesn't know or care which provider is being used. Swap with one config change.
