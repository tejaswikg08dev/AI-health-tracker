# 🚀 Phase 8 Part 03: Deployment — AWS Production

> **"Production on AWS: ECS Fargate runs the backend containers, RDS PostgreSQL handles the database, ElastiCache runs Redis, S3 stores exports, SES sends emails, CloudFront serves the React frontend, and ALB load-balances traffic. All behind a VPC with private subnets."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [Phase 8 Part 02: Staging (Free Tier)](./phase8-part02-deployment-staging-free.md) |
| **Next** | [Phase 8 Part 04: Lambda Deployment](./phase8-part04-deployment-lambda.md) |

---

## 1. AWS Architecture

```
Internet
   │
   ▼
CloudFront (CDN)
   │
   ├── Static assets → S3 bucket (React build: index.html, JS, CSS)
   │
   └── /api/* → ALB (Application Load Balancer)
                  │
                  ├── Target Group: ECS Fargate (backend containers)
                  │     ├── Task 1: FastAPI + Nginx sidecar
                  │     ├── Task 2: FastAPI + Nginx sidecar
                  │     └── Task 3: FastAPI + Nginx sidecar (auto-scaled)
                  │
                  ├── Target Group: ECS Fargate (Celery workers)
                  │     ├── Worker 1
                  │     └── Worker 2
                  │
                  └── (Health checks on /health endpoint)

Private Subnet:
   ├── RDS PostgreSQL 16 + pgvector (Multi-AZ)
   ├── ElastiCache Redis 7 (cluster mode)
   └── S3 VPC Endpoint (exports, documents)

External:
   ├── SES (email sending)
   ├── OpenAI API (LLM — production provider)
   └── CloudWatch (logs + metrics + alarms)
```

---

## 2. AWS Service Map

| Component | AWS Service | Local Equivalent | Monthly Cost (estimate) |
|-----------|-----------|------------------|------------------------|
| **Backend** | ECS Fargate (2 tasks) | Docker container | ~$30 |
| **Database** | RDS PostgreSQL 16 (db.t3.micro) | Docker PostgreSQL | ~$15 |
| **Cache** | ElastiCache Redis (cache.t3.micro) | Docker Redis | ~$12 |
| **Storage** | S3 | MinIO | ~$1 |
| **CDN** | CloudFront | Nginx (static) | ~$1 |
| **Email** | SES | Console provider | ~$0.10/1K emails |
| **LLM** | OpenAI API | Ollama | ~$5-20 (usage-based) |
| **DNS** | Route 53 | localhost | ~$0.50 |
| **Logging** | CloudWatch | stdout | ~$2 |
| **Load Balancer** | ALB | Nginx | ~$16 |
| **Total** | | | **~$80-100/month** |

---

## 3. Deployment Steps (High Level)

### 3a. Infrastructure (One-Time Setup)

```bash
# 1. Create VPC with public + private subnets
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# 2. Create RDS PostgreSQL with pgvector
aws rds create-db-instance \
  --db-instance-identifier health-tracker-db \
  --engine postgres --engine-version 16 \
  --db-instance-class db.t3.micro \
  --master-username healthuser \
  --master-user-password <password> \
  --allocated-storage 20

# 3. Enable pgvector extension
psql -h <rds-endpoint> -U healthuser -d healthtracker
> CREATE EXTENSION IF NOT EXISTS vector;

# 4. Create ElastiCache Redis
aws elasticache create-cache-cluster \
  --cache-cluster-id health-tracker-redis \
  --engine redis --engine-version 7.0 \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1

# 5. Create S3 bucket
aws s3 mb s3://health-tracker-prod

# 6. Create ECR repository
aws ecr create-repository --repository-name health-tracker-backend
```

### 3b. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build production image (stage 3 of Dockerfile)
docker build -t health-tracker-backend ./backend

# Tag and push
docker tag health-tracker-backend:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/health-tracker-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/health-tracker-backend:latest
```

### 3c. Create ECS Task Definition

```json
{
  "family": "health-tracker-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/health-tracker-backend:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql+asyncpg://...@rds-endpoint/healthtracker"},
        {"name": "REDIS_URL", "value": "redis://elasticache-endpoint:6379/0"},
        {"name": "LLM_PROVIDER", "value": "openai"},
        {"name": "EMAIL_PROVIDER", "value": "ses"},
        {"name": "APP_ENV", "value": "production"},
        {"name": "DEBUG", "value": "false"}
      ],
      "secrets": [
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:ssm:...:secret-key"},
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:ssm:...:openai-key"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/health-tracker",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### 3d. Deploy Frontend to S3 + CloudFront

```bash
# Build React app with production API URL
cd frontend
VITE_API_URL=https://api.healthtracker.app npm run build

# Upload to S3
aws s3 sync dist/ s3://health-tracker-frontend --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id <dist-id> \
  --paths "/*"
```

---

## 4. Production vs Local: What Changes

| Aspect | Local | Production |
|--------|-------|-----------|
| Server | uvicorn --reload | gunicorn -w 4 -k uvicorn.workers.UvicornWorker |
| Database | Docker container | RDS (managed, backups, Multi-AZ) |
| Secrets | `.env` file | AWS Systems Manager Parameter Store |
| HTTPS | None | ACM certificate + ALB termination |
| Scaling | 1 container | ECS auto-scaling (2-10 tasks) |
| Logs | stdout | CloudWatch Logs |
| LLM | Ollama (free, local) | OpenAI (paid, fast, reliable) |
| Email | Console (prints) | SES (real delivery) |

**Same code, different infrastructure.** The Strategy pattern and env-var config mean zero code changes between local and production.

---

## 5. Navigation

| ⬅️ Previous | [Phase 8 Part 02: Staging](./phase8-part02-deployment-staging-free.md) |
| ➡️ Next | [Phase 8 Part 04: Lambda Deployment](./phase8-part04-deployment-lambda.md) |

---

**End of Phase 8 Part 03: AWS Production Deployment**
