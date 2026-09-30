# Week 5 Learning Notes — Testing, CI/CD, Deployment, Documentation

## What I Learned

### Day 1-2: Testing
- [ ] pytest fixtures: conftest.py, shared setup/teardown
- [ ] Unit vs integration tests: what to mock, what to use real
- [ ] Mock objects: MockLLMClient, MockStorageProvider, MockEmailProvider
- [ ] Factory pattern for test data: make_habit_data() with random but valid data
- [ ] Async testing: pytest-asyncio, AsyncClient for FastAPI

### Day 3: CI/CD
- [ ] GitHub Actions: triggers, jobs, steps, services
- [ ] Service containers: PostgreSQL + Redis in CI (real databases!)
- [ ] Multi-stage pipeline: lint → test → build (fail fast)
- [ ] Environment variables in CI: secrets, not hardcoded

### Day 4: Nginx + Docker
- [ ] Reverse proxy: what it is and why needed
- [ ] Rate limiting: zone definition, burst, nodelay
- [ ] SSE support: proxy_buffering off
- [ ] Multi-stage Dockerfile: builder → development → production
- [ ] Docker Compose: service dependencies, health checks, volumes

### Day 5: Deployment + Documentation
- [ ] Staging: Render + Vercel + Supabase (free tier)
- [ ] Production: AWS architecture (documented, not deployed)
- [ ] HLD: system overview for stakeholders
- [ ] LLD: algorithms and implementation for engineers
- [ ] README: first thing anyone reads about the project

## Bugs I Hit and How I Fixed Them

1. **Error:** ...
   **Cause:** ...
   **Fix:** ...

## Final Reflection

What I'm most proud of building: ...

What was hardest to understand: ...

What I'd do differently next time: ...
