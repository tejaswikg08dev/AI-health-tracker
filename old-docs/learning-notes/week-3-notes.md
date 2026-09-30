# Week 3 Learning Notes — AI Module (LLM + RAG)

## What I Learned

### Day 1: LLM Integration
- [ ] Strategy pattern: abstract base + 3 implementations
- [ ] Factory pattern: get_llm_client() returns the right one
- [ ] Token counting: why it matters for cost and context window
- [ ] Prompt templates: Jinja2 for injecting data into prompts

### Day 2-3: RAG Pipeline
- [ ] PDF text extraction: PyPDF2, page-by-page tracking
- [ ] Chunking: recursive splitting, why overlap matters
- [ ] Embeddings: text → 768-dimension float vector (meaning capture)
- [ ] pgvector: cosine distance operator <=>, IVFFlat index
- [ ] Retrieval: embed query → search → filter by threshold → format with citations

### Day 4-5: Chat + Streaming
- [ ] SSE: Server-Sent Events for word-by-word response
- [ ] async generators: yield tokens as they're generated
- [ ] Chat history: storing + retrieving for conversation context

## Bugs I Hit and How I Fixed Them

1. **Error:** ...
   **Cause:** ...
   **Fix:** ...
