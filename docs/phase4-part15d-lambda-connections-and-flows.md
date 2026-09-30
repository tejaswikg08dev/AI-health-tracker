# 🔄 Phase 4 Part 15d: Lambda — Connections & Flows

> **"A daily timeline of all 6 Lambdas, end-to-end flows for SQS and S3 triggers, and the complete deployment pipeline."**

---

## 1. Daily Lambda Timeline

```
08:00 AM UTC — Lambda 1: daily_reminder
  Trigger: EventBridge cron
  → Query users with reminders ON + haven't logged today
  → Send SES emails to qualifying users
  Duration: ~5-15s | Emails: ~20-30

09:00 AM UTC (Sundays only) — Lambda 2: weekly_report
  Trigger: EventBridge cron
  → For each user: gather data → Groq LLM analysis → HTML report
  → Save to S3 + send email
  Duration: ~2-5 min | Reports: ~50

Throughout the day — Lambda 3: csv_export (on-demand)
  Trigger: SQS message (when user requests large export)
  → Generate CSV → upload to S3 → email presigned URL
  Duration: ~5-15s per export

Throughout the day — Lambda 4: streak_milestone (after each log)
  Trigger: SQS message (after habit log creation)
  → Calculate streak → check milestone → celebrate if hit
  Duration: ~2-5s per check

00:00 AM UTC (1st of month) — Lambda 5: data_cleanup
  Trigger: EventBridge cron
  → Delete: old chats (90d), old insights (180d), failed docs (30d)
  → VACUUM ANALYZE on large tables
  Duration: ~5-30s

Throughout the day — Lambda 6: document_processor (on upload)
  Trigger: S3 event (file uploaded to documents/ prefix)
  → Download → extract text → chunk → embed → store in pgvector
  Duration: ~10-60s per document
```

---

## 2. Flow: User Logs Habit → Streak Milestone Email

```
USER: Logs "Water Intake = 8 glasses" for today (Sep 26)

 1  FastAPI POST /logs
      → LogService.create_log() → INSERT INTO habit_logs
      → session.commit()

 2  FastAPI sends SQS message:
      sqs.send_message(QueueUrl="health-tracker-streak", MessageBody=json.dumps({
        "user_id": "uuid-001", "habit_id": "water-uuid"
      }))
      → API returns 201 immediately (SQS is async)

 3  SQS delivers message to Lambda 4 (streak_milestone)

 4  Lambda 4:
      → SELECT email, full_name FROM users WHERE id = 'uuid-001'
      → SELECT name FROM habits WHERE id = 'water-uuid'
      → Gaps-and-islands SQL: current_streak = 30 days
      → 30 ∈ MILESTONES? → YES!
      → Already sent? → SELECT FROM ai_insights WHERE title LIKE '%Water%30%' → NO
      → INSERT INTO ai_insights (streak_milestone record)
      → send_email("🔥 30-Day Streak on Water Intake!")

 5  User receives email: "🔥 30-Day Streak! Incredible work, Shreya!"

TOTAL: API response in ~200ms. Email arrives ~5-10 seconds later.
User doesn't wait for streak check — it's completely async.
```

---

## 3. Flow: User Uploads PDF → RAG Processing

```
USER: Uploads "Sleep Guide.pdf" via POST /ai/documents

 1  FastAPI:
      → INSERT INTO documents (status='processing')
      → Upload PDF to S3: documents/{user_id}/{doc_id}/Sleep Guide.pdf
      → Return 201: {"id":"doc-id", "status":"processing"}

 2  S3 triggers Lambda 6 (document_processor) on PutObject event

 3  Lambda 6:
      → Download "Sleep Guide.pdf" from S3
      → PyPDF2: extract text from 50 pages → ~25,000 words
      → Chunk: 100 chunks × ~500 tokens, 200-char overlap
      → Embed: 100 × 768-dim vectors (placeholder zeros or Groq API)
      → INSERT INTO document_chunks × 100 (with ::vector cast)
      → UPDATE documents SET status='processed', chunk_count=100

 4  User refreshes document list:
      GET /ai/documents → {"status":"processed", "chunk_count":100}

 5  User asks: "What foods help sleep?"
      → Agent calls search_docs tool
      → pgvector: SELECT ... ORDER BY embedding <=> query_vec LIMIT 5
      → Top chunks from Sleep Guide returned as context
      → AI answers with citations: "Based on your Sleep Guide (p.3)..."

TOTAL: Upload returns instantly. Processing takes ~30-60 seconds.
Document is searchable after Lambda completes.
```

---

## 4. SAM Deployment Flow

```bash
cd lambda_functions/

# Step 1: Build
sam build
  → Packages each function directory + shared/ into ZIP files
  → Creates .aws-sam/build/ with deployment artifacts

# Step 2: Deploy (first time)
sam deploy --guided
  → Asks: stack name? region? parameter values?
  → Creates CloudFormation stack
  → Provisions: 6 Lambdas + 2 SQS queues + 1 S3 bucket + EventBridge rules
  → Sets environment variables from Parameters

# Step 3: Verify
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `health`)].FunctionName'
  → DailyReminderFunction, WeeklyReportFunction, CsvExportFunction, ...

# Test locally
sam local invoke DailyReminderFunction --event events/daily.json
  → Runs in Docker container simulating Lambda environment
```

---

## 5. Lambda Module Summary

### What You Built (Parts 15–15d)

| Part | Files | What It Does |
|------|-------|-------------|
| **15** | — | Overview: 6 functions, 3 triggers, Lambda vs Celery |
| **15a** | 4 shared + template.yaml | Utilities + SAM infrastructure-as-code |
| **15b** | 3 handlers | Scheduled: daily reminder, weekly report, cleanup |
| **15c** | 3 handlers | Event-driven: CSV export, streak milestone, doc processor |
| **15d** | (this doc) | Timeline, flows, deployment |

### By the Numbers

| Metric | Value |
|--------|-------|
| Lambda functions | 6 |
| Shared utility files | 4 (config, db, email, S3) |
| Trigger types | 3 (EventBridge cron, SQS, S3 event) |
| SQS queues | 2 (export, streak) |
| S3 buckets | 1 (documents + exports) |
| Monthly cost (free tier) | $0 |
| Max execution time | 15 min (weekly report) |
| Max memory | 512 MB (weekly report, doc processor) |

### Lambda Module — All Sub-Parts Complete ✅

| Sub-Part | Status |
|----------|--------|
| 15a | ✅ Shared + SAM Template |
| 15b | ✅ Scheduled Functions (Lambdas 1, 2, 5) |
| 15c | ✅ Event-Driven Functions (Lambdas 3, 4, 6) |
| **15d** | ✅ **Connections & Flows** |

---

## 6. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 15c: Event-Driven Functions](./phase4-part15c-lambda-event-driven-functions.md) |
| ➡️ Next | [Part 16: Frontend Overview](./phase4-part16-frontend-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**🎉 The Lambda module is COMPLETE.**

*6 serverless functions: daily reminders, weekly AI reports, CSV exports, streak celebrations, data cleanup, and document processing. All defined in one SAM template, deployed with one command, running at $0 on free tier. Next: the Frontend module — React, TypeScript, TanStack Query, Recharts.*
