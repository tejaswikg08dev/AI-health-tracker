# Lambda Deployment Guide

## Overview

6 Lambda functions deployed via AWS SAM (Serverless Application Model).

| Function | Trigger | Schedule |
|----------|---------|----------|
| Daily Reminder | EventBridge cron | 8 AM UTC daily |
| Weekly Report | EventBridge cron | Sunday 9 AM UTC |
| CSV Export | SQS message | On demand |
| Streak Milestone | SQS message | On new log |
| Data Cleanup | EventBridge cron | 1st of month |
| Document Processor | S3 PutObject | On upload |

## Prerequisites

- AWS CLI configured: `aws configure`
- SAM CLI installed: [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Docker (SAM builds Lambda packages in Docker)

## Deploy

```bash
cd lambda_functions

# Build all functions
sam build

# First deployment (interactive — sets stack name, region, parameters)
sam deploy --guided

# Subsequent deployments
sam deploy
```

## Local Testing

```bash
# Test with sample event
sam local invoke DailyReminderFunction --event events/daily_reminder_event.json

# Test SQS-triggered function
sam local invoke CsvExportFunction --event events/sqs_export_event.json
```

## Environment Variables

Set these in the SAM deploy parameters or in the AWS Console:

```
DATABASE_URL     — PostgreSQL connection string (RDS endpoint)
S3_BUCKET        — S3 bucket name for exports and documents
SES_FROM_EMAIL   — Verified SES sender email
GROQ_API_KEY     — Groq API key (for weekly report AI analysis)
```

## Cost (Free Tier)

All 6 functions combined use < 0.01% of Lambda free tier:
- ~80 invocations/month
- ~272 GB-seconds/month
- Free tier: 1,000,000 invocations + 400,000 GB-seconds
