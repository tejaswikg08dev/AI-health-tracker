# 🚀 Phase 8 Part 04: Deployment — Lambda Functions (SAM)

> **"Deploy all 6 Lambda functions with one command: `sam deploy`. SAM packages each handler with the shared/ utilities, creates SQS queues and S3 buckets, configures EventBridge cron triggers, and sets up environment variables from Parameters."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [Phase 8 Part 03: AWS Production](./phase8-part03-deployment-aws-production.md) |
| **Next** | [Phase 9: Nginx & Monitoring](./phase9-part01-nginx-monitoring.md) |

---

## 1. SAM Deployment Commands

```bash
cd lambda_functions/

# ── Step 1: Build ──
# Packages each function + shared/ into deployment artifacts
sam build
# Creates .aws-sam/build/ with 6 function directories

# ── Step 2: Deploy (First Time — Interactive) ──
sam deploy --guided
# Prompts for:
#   Stack name: health-tracker-lambdas
#   Region: us-east-1
#   Parameter values: DatabaseHost, SecretKey, etc.
#   Confirm changeset: y
#   Allow IAM role creation: y
#   Save config: y (creates samconfig.toml)

# ── Subsequent Deploys ──
sam deploy
# Uses saved config from samconfig.toml — no prompts

# ── Step 3: Verify ──
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `health`)].FunctionName' \
  --output table
```

---

## 2. What SAM Creates

```
CloudFormation Stack: health-tracker-lambdas
│
├── 6 Lambda Functions
│   ├── DailyReminderFunction     (EventBridge: 8 AM daily)
│   ├── WeeklyReportFunction      (EventBridge: Sunday 9 AM)
│   ├── CsvExportFunction         (SQS: health-tracker-export)
│   ├── StreakMilestoneFunction    (SQS: health-tracker-streak)
│   ├── DataCleanupFunction       (EventBridge: 1st of month)
│   └── DocumentProcessorFunction (S3: documents/ prefix)
│
├── 2 SQS Queues
│   ├── health-tracker-export-queue
│   └── health-tracker-streak-queue
│
├── 1 S3 Bucket
│   └── health-tracker-documents-{account-id}
│
├── 3 EventBridge Rules (cron triggers)
│
└── IAM Roles (auto-created per function)
    └── Permissions: RDS access, SQS, S3, SES, CloudWatch Logs
```

---

## 3. Testing Locally with SAM

```bash
# Test a single function locally (runs in Docker)
sam local invoke DailyReminderFunction --event events/daily.json

# Example events/daily.json:
{
  "source": "aws.events",
  "detail-type": "Scheduled Event"
}

# Test SQS-triggered function:
sam local invoke CsvExportFunction --event events/export.json

# Example events/export.json:
{
  "Records": [{
    "body": "{\"user_id\": \"uuid-001\", \"start_date\": \"2026-01-01\", \"end_date\": \"2026-09-26\", \"user_email\": \"shreya@test.com\", \"user_name\": \"Shreya\"}"
  }]
}

# Start all functions as a local API (for HTTP-triggered Lambdas):
sam local start-api
```

---

## 4. Lambda vs Backend: When to Use Each

| Feature | Backend (ECS/FastAPI) | Lambda |
|---------|----------------------|--------|
| **User-facing API** | ✅ All 38 endpoints | ❌ |
| **Scheduled jobs** | Celery Beat (alternative) | ✅ EventBridge cron |
| **Event processing** | ❌ | ✅ SQS, S3 triggers |
| **Always running** | ✅ (containers always on) | ❌ (cold start per invoke) |
| **Cost model** | Per-hour (even when idle) | Per-invocation ($0 when idle) |
| **Max runtime** | Unlimited | 15 min |
| **Best for** | Request/response APIs | Background jobs, events |

**Our approach:** FastAPI handles ALL user-facing requests. Lambda handles scheduled tasks (reminders, reports, cleanup) and event-driven processing (exports, streaks, documents). This is the standard serverless + containers hybrid pattern.

---

## 5. Cost Estimate (Lambda)

| Function | Invocations/Month | Duration | Cost |
|----------|-------------------|----------|------|
| Daily Reminder | 30 | ~5s each | $0.00 |
| Weekly Report | 4 | ~60s each | $0.00 |
| Data Cleanup | 1 | ~10s | $0.00 |
| CSV Export | ~50 | ~10s each | $0.00 |
| Streak Milestone | ~500 | ~3s each | $0.00 |
| Document Processor | ~20 | ~30s each | $0.00 |
| **Total** | **~605** | | **$0.00** (free tier: 1M invocations) |

---

## 6. Navigation

| ⬅️ Previous | [Phase 8 Part 03: AWS Production](./phase8-part03-deployment-aws-production.md) |
| ➡️ Next | [Phase 9: Nginx & Monitoring](./phase9-part01-nginx-monitoring.md) |

---

**🎉 Phase 8 (Deployment) is COMPLETE.**

*Four deployment targets: local (Docker Compose), staging (free tier services), AWS production (ECS + RDS + ElastiCache), Lambda (SAM). Same code runs everywhere — configuration controls which providers are used. Next: Nginx reverse proxy and monitoring.*
