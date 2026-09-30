# Week 1 Learning Notes — Backend Foundation + Auth + Habits + Logs

_Fill this in as you read and run the code. Write in your own words._

## What I Learned Today

### Day 1: Project Setup
- [ ] Docker Compose: what each service does
- [ ] .env files: why never commit secrets
- [ ] Makefile: shortcut commands

### Day 2: FastAPI Foundation
- [ ] App factory pattern (create_app)
- [ ] Lifespan events (startup/shutdown)
- [ ] Dependency injection (Depends)
- [ ] How middleware works (request → chain → response)

### Day 3: Auth System
- [ ] bcrypt: why hashing is one-way, what salt is
- [ ] JWT: what's in the payload, how signature works
- [ ] Access vs refresh tokens: why two tokens
- [ ] Token blacklist in Redis: why Redis not database

### Day 4: Habits Module
- [ ] Repository pattern: why separate from service
- [ ] Soft delete (is_archived): why not hard delete
- [ ] Pydantic validation: field_validator, Field()
- [ ] UUID vs auto-increment: trade-offs

### Day 5: Logs Module
- [ ] Unique constraint: (user_id, habit_id, log_date)
- [ ] Bulk upsert: create-or-update pattern
- [ ] Cache invalidation: when and why
- [ ] Type-specific validation: numeric vs boolean vs scale

### Day 6-7: Analytics
- [ ] Window functions: ROW_NUMBER, PARTITION BY
- [ ] CTEs: WITH clause for readable queries
- [ ] Redis cache-aside: check → miss → compute → cache
- [ ] Pearson correlation: the math and the meaning

## Bugs I Hit and How I Fixed Them

_Write down every error you encounter — this becomes interview material._

1. **Error:** ...
   **Cause:** ...
   **Fix:** ...

## Questions I Still Have

1. ...
2. ...
