# Week 4 Learning Notes — AI Agents + Workflows + Lambda

## What I Learned

### Day 1-2: ReAct Agent
- [ ] ReAct loop: think → act → observe → repeat
- [ ] Tool calling: OpenAI function calling format (name, description, parameters)
- [ ] Max iterations: why cap at 5 (prevent infinite loops)
- [ ] Tool execution: agent calls tool → gets result → feeds back to LLM

### Day 3: Agent Memory
- [ ] Short-term: sliding window buffer (last 20 messages)
- [ ] Long-term: Redis hash with TTL (persists across sessions)
- [ ] Why both: follow-up questions (short) vs remembering preferences (long)

### Day 4-5: Agentic Workflow
- [ ] Pipeline pattern: DataCollector → Analyzer → ReportWriter
- [ ] Orchestrator: retry logic, timeout, graceful degradation
- [ ] Why 3 agents > 1: specialized prompts produce better output

### Day 6-7: Lambda Functions
- [ ] EventBridge cron triggers: scheduled tasks without servers
- [ ] SQS triggers: event-driven processing (async export)
- [ ] S3 triggers: react to file uploads (document processing)
- [ ] SAM template: infrastructure as code for Lambda
- [ ] Connection reuse: warm starts in Lambda

## Bugs I Hit and How I Fixed Them

1. **Error:** ...
   **Cause:** ...
   **Fix:** ...
