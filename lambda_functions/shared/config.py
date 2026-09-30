# Lambda environment configuration — reads from Lambda env vars
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://healthuser:healthpass@localhost:5432/healthtracker")
S3_BUCKET = os.environ.get("S3_BUCKET", "health-tracker")
S3_REGION = os.environ.get("AWS_REGION", "us-east-1")
SES_FROM_EMAIL = os.environ.get("SES_FROM_EMAIL", "noreply@healthtracker.app")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
