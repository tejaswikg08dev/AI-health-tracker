# AWS Production Deployment — Reference Architecture

This documents the production AWS architecture. You won't deploy this (costs money), but you'll explain it in interviews.

## Architecture

```
Route 53 (DNS)
    ↓
CloudFront (CDN) → S3 (React static files)
    ↓ /api/*
ALB (Application Load Balancer)
    ↓
ECS Fargate Cluster
├── FastAPI Service (2-10 tasks, auto-scaling)
│   └── Nginx sidecar container
├── Celery Worker (1-5 tasks)
└── Celery Beat (1 task, singleton)
    ↓              ↓              ↓
RDS PostgreSQL   ElastiCache    S3 (files)
(Multi-AZ)       (Redis cluster)
    ↓
AWS Bedrock (LLM) — replaces Ollama/Groq in production
```

## AWS Services Used

| Service | Purpose | Est. Cost |
|---------|---------|-----------|
| ECS Fargate | Run containers (no server management) | ~$30-50/mo |
| RDS PostgreSQL | Managed database, Multi-AZ, backups | ~$15-30/mo |
| ElastiCache Redis | Managed Redis, failover | ~$15/mo |
| S3 | Static files, exports, documents | ~$1-5/mo |
| CloudFront | CDN for global frontend delivery | ~$1-5/mo |
| ALB | Load balancer, health checks | ~$16/mo |
| ECR | Docker image registry | ~$1/mo |
| Bedrock | Managed LLM (Claude/Llama) | ~$10-50/mo |
| SES | Email delivery | ~$0.10/1000 emails |
| Lambda (6 functions) | Event-driven tasks | ~$0/mo (free tier) |
| SQS | Message queues | ~$0/mo (free tier) |
| EventBridge | Cron scheduling | $0/mo (free) |
| CloudWatch | Logs, metrics, alarms | ~$5/mo |
| WAF | Web Application Firewall | ~$5/mo |
| Secrets Manager | Store API keys securely | ~$1/mo |
| **Total** | | **~$100-180/mo** |

## Key Production Differences

| Aspect | Local Dev | Production |
|--------|-----------|------------|
| LLM | Ollama (free, local) | AWS Bedrock (managed, auto-scale) |
| Database | Docker PostgreSQL | RDS Multi-AZ (auto-failover) |
| Redis | Docker Redis | ElastiCache (cluster, replication) |
| Storage | MinIO (local S3) | Real S3 + CloudFront CDN |
| Email | Console (print) | SES (deliverability, bounce handling) |
| Secrets | .env file | Secrets Manager (encrypted, rotated) |
| Logs | stdout | CloudWatch + OpenSearch |
| SSL | None (HTTP) | ACM certificate + CloudFront |
| Networking | Docker bridge | VPC, private subnets, security groups |

## Deploy Command (SAM for Lambda)
```bash
cd lambda_functions
sam build
sam deploy --guided   # First time: interactive setup
sam deploy            # Subsequent: uses saved config
```
