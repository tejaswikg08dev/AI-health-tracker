# 🧠 Phase 0 — Part 05: AI Concepts from Zero

> **"You don't need a PhD in machine learning. You need to understand 10 concepts and how they connect."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 0 — Overview & Setup |
| **Part** | 05 of 05 |
| **Previous** | [Part 04 — Environment Setup](./phase0-part04-environment-setup.md) |
| **Next** | [Phase 1 — System Design](./phase1-part01-system-design-overview.md) |
| **Time to Read** | ~30 minutes |

---

## The 10 AI Concepts You Need

```
1. LLM ────────────── The brain (generates text)
2. Tokens ─────────── How AI reads text (not words, not characters)
3. Prompt ─────────── The instruction you give the AI
4. Temperature ────── How creative vs focused the AI is
5. Embeddings ─────── Converting text to numbers (meaning as math)
6. Vector Database ── Searching by meaning (not keywords)
7. RAG ────────────── Give the AI YOUR data before it answers
8. Chunking ───────── Splitting documents into searchable pieces
9. Agent ──────────── AI that can THINK, USE TOOLS, and DECIDE
10. Agentic Workflow ── Multiple agents working in a pipeline
```

---

## 1. What is an LLM?

**LLM = Large Language Model.** A neural network trained on billions of text documents that predicts the next word.

**Analogy:** Autocomplete on steroids. Your phone predicts the next word when you text. An LLM does the same but trained on the entire internet — it can write essays, answer questions, write code.

**How it actually works (simplified):**
```
Input:  "The capital of France is"
Model:  Checks billions of patterns it learned
Output: "Paris" (87% confident)
        "Lyon" (5%)
        "a city" (3%)
        ... (other possibilities)
```

It does NOT "understand" or "know" anything. It's very sophisticated pattern matching. This is why it sometimes makes up facts ("hallucination") — the pattern says it SHOULD produce text, even if the facts are wrong.

### LLMs in Our Project

| Provider | Model | Where | Cost |
|----------|-------|-------|------|
| Ollama | Llama 3.1 (8B params) | Your laptop | $0 |
| Groq | Llama 3.1 (8B) | Cloud server | $0 (free tier) |
| OpenAI | GPT-4 | Cloud server | ~$0.03/1K tokens |

---

## 2. What are Tokens?

LLMs don't read words — they read **tokens**. A token is approximately 4 characters or ¾ of a word.

```
"Hello, how are you?"
Tokens: ["Hello", ",", " how", " are", " you", "?"]
Count: 6 tokens

"The patient's hemoglobin level is 12.5 g/dL"
Tokens: ["The", " patient", "'s", " hem", "oglobin", " level", " is", " 12", ".", "5", " g", "/", "dL"]
Count: 13 tokens
```

### Why Tokens Matter

| What | Why |
|------|-----|
| **Cost** | OpenAI charges per token ($0.03 per 1,000 input tokens for GPT-4) |
| **Context window** | Llama 3.1 can process 128K tokens max. Your entire conversation + context must fit |
| **Speed** | More tokens = slower response. 100 tokens ≈ 0.5 seconds |

### In Our Project
Our `token_tracker.py` counts tokens per user per day. Daily limit: 50,000 tokens (~50 conversations with context).

---

## 3. What is a Prompt?

A prompt is the **text you send to the LLM**. It includes instructions, context, and the user's question.

```
PROMPT = [
    SYSTEM: "You are a friendly health coach. Reference actual data.
             Keep responses under 5 sentences."
    
    USER DATA: "Sleep this week: Mon 6h, Tue 5h, Wed 7h, Thu 5.5h"
    
    USER QUESTION: "Why am I tired this week?"
]

LLM RESPONSE: "Looking at your data, you averaged 5.9 hours of sleep
this week — well below the recommended 7-8 hours. Tuesday and Thursday
were particularly low at 5 and 5.5 hours. Try setting a consistent
bedtime alarm for 10:30 PM to hit at least 7 hours."
```

### Prompt Engineering
The art of writing prompts that get good responses. Small changes in the prompt = big changes in output quality.

| Prompt | Quality |
|--------|---------|
| "Tell me about sleep" | Vague, generic answer |
| "You are a health coach. Based on this data: [Mon 6h, Tue 5h...], why am I tired?" | Specific, data-driven answer |

Our `prompt_templates.py` has 6 carefully crafted Jinja2 templates for different use cases.

---

## 4. What is Temperature?

Temperature controls **how random/creative** the LLM's output is.

```
Temperature 0.0 → Always picks the most likely word → DETERMINISTIC
  "The capital of France is Paris." (same every time)

Temperature 0.5 → Usually picks likely words → BALANCED
  "The capital of France is the beautiful city of Paris." (slight variation)

Temperature 1.0 → Sometimes picks unlikely words → CREATIVE
  "The capital of France is a living museum of art and revolution." (very different each time)
```

### In Our Project

| Use Case | Temperature | Why |
|----------|-------------|-----|
| Agent reasoning | 0.3 | Focus — need accurate tool decisions |
| Health insights | 0.4 | Mostly factual with slight creativity |
| Report writing | 0.6 | More creative, engaging prose |
| General chat | 0.7 | Conversational, natural |

---

## 5. What are Embeddings?

An embedding converts text into a **list of numbers** (a vector) that captures the text's MEANING.

```
"I drank 8 glasses of water" → [0.12, -0.45, 0.78, ..., 0.33]  (768 numbers)
"My water intake was 8 cups" → [0.11, -0.44, 0.79, ..., 0.34]  (similar numbers!)
"The weather is sunny today" → [0.89, 0.23, -0.56, ..., -0.12]  (very different numbers)
```

The first two vectors are CLOSE (similar meaning). The third is FAR (different topic).

**Analogy:** GPS coordinates for meaning. Just like [12.97, 77.59] is Bangalore and [12.98, 77.60] is also Bangalore (close!), while [40.71, -74.01] is New York (far!), embeddings put similar meanings in nearby locations in 768-dimensional space.

### Why 768 Numbers?
The embedding model (nomic-embed-text) was trained to use 768 dimensions. More dimensions = more nuance but more storage. 768 is a good balance.

---

## 6. What is a Vector Database?

A database optimized for **searching by similarity** instead of exact matching.

```
TRADITIONAL DATABASE (keyword search):
  Query: "water consumption"
  SQL: SELECT * FROM docs WHERE text LIKE '%water consumption%'
  MISSES: "hydration level" (same meaning, different words!)

VECTOR DATABASE (semantic search):
  Query: "water consumption" → embed → [0.12, -0.45, ...]
  Search: find vectors closest to [0.12, -0.45, ...]
  FINDS: "hydration level" (similar meaning → similar vector → match!)
```

### pgvector in Our Project
We use PostgreSQL + pgvector. The `<=>` operator calculates **cosine distance** between two vectors:

```sql
SELECT chunk_text, 1 - (embedding <=> query_vector) AS similarity
FROM document_chunks
WHERE 1 - (embedding <=> query_vector) > 0.3  -- only relevant results
ORDER BY embedding <=> query_vector  -- closest first
LIMIT 5;
```

### Cosine Similarity
```
similarity = 1.0 → identical meaning
similarity = 0.5 → somewhat related
similarity = 0.0 → completely unrelated
```

---

## 7. What is RAG?

**RAG = Retrieval-Augmented Generation.**

Instead of asking the LLM from its training data (which can be wrong or outdated), we RETRIEVE relevant info from YOUR documents and AUGMENT the prompt with it before GENERATING the answer.

```
WITHOUT RAG:
  User: "What's my iron level?"
  LLM: "Normal iron levels are 60-170 µg/dL." (generic, not YOUR data)

WITH RAG:
  User: "What's my iron level?"
  System: [searches your uploaded blood report] → finds "Iron: 45 µg/dL"
  LLM: "Based on your blood report from March 15 [Source: blood_report.pdf, p.2],
        your iron level is 45 µg/dL, which is below the normal range (60-170 µg/dL).
        Since you mentioned being vegetarian, consider iron-rich foods like spinach
        and lentils."
```

### RAG Pipeline in Our Project

```
INGESTION (upload time):
  PDF → Extract text (PyPDF2)
      → Split into chunks (500 tokens, 50 overlap)
      → Embed each chunk (nomic-embed-text → 768 floats)
      → Store chunks + vectors in pgvector

RETRIEVAL (query time):
  User question → Embed question → Search pgvector (cosine similarity)
  → Top 5 chunks → Format with citations → Inject into LLM prompt
  → LLM answers using YOUR document data
```

---

## 8. What is Chunking?

Splitting a document into smaller pieces for embedding and retrieval.

### Why Not Embed the Whole Document?
1. **Token limit:** A 50-page PDF is ~25,000 tokens. Llama 3.1's context is 128K, but you need room for the question, instructions, and response
2. **Precision:** If the answer is on page 15, we want to retrieve JUST that section, not the entire 50 pages
3. **Embedding quality:** Embeddings are more meaningful for short text (500 tokens) than long text (25,000 tokens)

### Overlap
```
WITHOUT OVERLAP:
  Chunk 1: "...the patient's iron level is"
  Chunk 2: "45 µg/dL which is below normal..."
  PROBLEM: Neither chunk has the complete sentence!

WITH 50-TOKEN OVERLAP:
  Chunk 1: "...the patient's iron level is 45 µg/dL which"
  Chunk 2: "iron level is 45 µg/dL which is below normal..."
  SOLUTION: Both chunks have the full information!
```

Our `chunker.py` uses recursive splitting: try paragraph boundaries first, then sentences, then words.

---

## 9. What is an AI Agent?

An agent is an LLM that can **THINK, USE TOOLS, and DECIDE** — not just generate text.

```
CHATBOT (simple LLM):
  User: "How's my sleep?"
  LLM: "Sleep is important for health. You should aim for 7-8 hours."
  (Generic — doesn't know YOUR data)

AGENT (LLM + tools):
  User: "How's my sleep?"
  THINK: "I need the user's actual sleep data"
  ACT: → calls query_logs(habit="Sleep", days=7) → gets [6, 5, 7, 5.5, 6, 8, 7]
  THINK: "Average is 6.4 hours. Let me check if this correlates with mood"
  ACT: → calls correlate(habit_a="Sleep", habit_b="Mood") → r=0.72
  THINK: "Strong correlation found. I have enough data now."
  ANSWER: "You averaged 6.4 hours of sleep this week — below the 7-8 hour
           recommendation. I found a strong correlation (0.72) between your
           sleep and mood scores, meaning your mood tends to be higher on
           days you sleep more."
```

### The ReAct Pattern (Reason + Act)
```
1. THINK  → LLM reasons about what information it needs
2. ACT    → LLM calls a tool (database query, document search, etc.)
3. OBSERVE → Agent shows the tool's result to the LLM
4. REPEAT → LLM decides: need more data? → goto 1. Have enough? → answer.
```

Our agent has 5 tools: query_logs, get_analytics, search_documents, correlate, create_plan.

---

## 10. What is an Agentic Workflow?

Multiple agents/steps working in a **pipeline** — each specializing in one task.

```
SINGLE AGENT: One agent does everything → mediocre at everything

AGENTIC WORKFLOW:
  Step 1: DataCollector agent → gathers all data (Python, no LLM)
  Step 2: Analyzer agent → finds patterns and insights (LLM)
  Step 3: ReportWriter agent → writes personalized report (LLM)
  
  Each agent is SPECIALIZED → better results than one generalist
```

### Our Weekly Report Pipeline
```
DataCollector
  → "Here's all habit data for the week, streaks, weekly comparison..."
  ↓ (passes data_summary to next step)
Analyzer
  → "Top improvements: sleep up 12%. Concerning: water intake dropped 20%"
  ↓ (passes analysis to next step)
ReportWriter
  → "Hey Shreya! Great week overall — your sleep improved to 7.2 hours..."
```

The Orchestrator manages: step sequencing, retry on failure (max 2 retries), timeout handling, logging.

---

## 🔄 How All 10 Concepts Connect

```
User asks: "Why am I tired this week?"
                    │
                    ▼
            ┌───── AGENT ─────┐ (concept 9)
            │  ReAct Loop     │
            │  THINK→ACT→OBS  │
            │                 │
            │  Uses TOOLS:    │
            │  ├── query_logs │──→ PostgreSQL (gets sleep data)
            │  ├── correlate  │──→ Python math (Pearson r)
            │  └── search_docs│──→ RAG PIPELINE (concept 7)
            │                 │        │
            │                 │    ┌───▼──────────────────┐
            │                 │    │ EMBED question       │ (concept 5)
            │                 │    │ → VECTOR search      │ (concept 6)
            │                 │    │ → retrieve CHUNKS    │ (concept 8)
            │                 │    │ → format citations   │
            │                 │    └───┬──────────────────┘
            │                 │        │
            │  All context    │◄───────┘
            │  gathered       │
            └────────┬────────┘
                     │
                     ▼
              ┌──── LLM ────┐ (concept 1)
              │ PROMPT with: │ (concept 3)
              │ ├── system   │
              │ ├── data     │
              │ ├── RAG ctx  │
              │ └── question │
              │              │
              │ TEMPERATURE  │ (concept 4)
              │ = 0.3 (focus)│
              │              │
              │ Output uses  │
              │ ~500 TOKENS  │ (concept 2)
              └──────┬───────┘
                     │
                     ▼
              "You averaged 6.4 hours of sleep this week.
               Based on your blood report [Source: report.pdf, p.3],
               your iron is low which can cause fatigue..."
```

---

## 🎤 Interview Q&A

### Q: "Explain RAG in simple terms"

> "RAG stands for Retrieval-Augmented Generation. Instead of relying on the LLM's training data, which can be outdated or wrong, we retrieve relevant information from the user's own documents and inject it into the prompt. In my project, users upload health PDFs. I chunk them into 500-token pieces, embed each chunk with nomic-embed-text (768 dimensions), store the vectors in pgvector, and when the user asks a question, I embed the question, find the 5 most similar chunks via cosine similarity, format them with source citations, and send them to the LLM as context."

### Q: "What's the difference between a chatbot and an AI agent?"

> "A chatbot makes one LLM call: question in, answer out. An agent runs a loop: it THINKS about what information it needs, CALLS a tool (database query, document search), OBSERVES the result, and decides whether to call another tool or generate its final answer. My health coach agent has 5 tools and makes up to 5 tool calls per question. This means it answers 'Why am I tired?' with actual sleep data (6.4 hours avg), real correlations (sleep-mood r=0.72), and cited document references — not generic health advice."

### Q: "What is an embedding?"

> "An embedding is a list of numbers — 768 floating-point values — that captures the meaning of a text. Similar meanings produce similar numbers. 'I drank 8 glasses of water' and 'My hydration level was high' produce vectors that are close together in 768-dimensional space, even though they share no common words. This enables semantic search: instead of matching keywords, we match meaning. I use cosine similarity to measure closeness — 1.0 is identical, 0.0 is unrelated."

### Q: "Why chunk documents instead of embedding the whole thing?"

> "Three reasons. First, LLMs have token limits — a 50-page PDF is ~25,000 tokens, which would consume most of the context window leaving no room for the question and response. Second, precision — if the answer is on page 15, I want to retrieve just that section, not pages 1-50. Third, embedding quality — embeddings capture meaning better for shorter text. I use 500-token chunks with 50-token overlap so information at chunk boundaries isn't lost."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 04 — Environment Setup](./phase0-part04-environment-setup.md) | | [Phase 1 — System Design](./phase1-part01-system-design-overview.md) |
