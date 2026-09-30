# Local Development Setup

## Prerequisites

- **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/)
- **Python 3.11+** — [download](https://www.python.org/downloads/)
- **Node.js 20+** — [download](https://nodejs.org/)
- **Git** — [download](https://git-scm.com/)

## Step-by-Step

### 1. Clone the repository
```bash
git clone https://github.com/your-username/health-tracker.git
cd health-tracker
```

### 2. Create environment file
```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 3. Start databases (PostgreSQL + Redis)
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up postgres redis minio -d
```

Wait 10 seconds for containers to be healthy:
```bash
docker-compose ps   # All should show "healthy"
```

### 4. Backend setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Run database migrations
alembic upgrade head

# Seed demo data
python -m scripts.seed_data

# Start the server (with hot reload)
uvicorn app.main:app --reload --port 8000
```

### 5. Frontend setup (new terminal)
```bash
cd frontend
npm install
npm run dev
```

### 6. Access the app
- **Frontend:** http://localhost:3000
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc
- **MinIO Console:** http://localhost:9001 (minioadmin / minioadmin)

### 7. Demo login
- **Email:** shreya@example.com
- **Password:** DemoPass123

## Optional: Start AI (Ollama)
```bash
# Start Ollama container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up ollama -d

# Pull the required models (first time only, ~5GB download)
docker-compose exec ollama ollama pull llama3.1:8b
docker-compose exec ollama ollama pull nomic-embed-text
```

## Useful Commands
```bash
make dev          # Start everything with hot reload
make test         # Run all tests
make test-unit    # Run unit tests only
make lint         # Run ruff + mypy
make migrate      # Run database migrations
make seed         # Seed demo data
make logs         # Follow container logs
make clean        # Stop everything and remove volumes
```

## Troubleshooting

**Port already in use:**
```bash
# Check what's using the port
netstat -ano | findstr :8000    # Windows
lsof -i :8000                  # Mac/Linux
```

**Database connection refused:**
- Make sure PostgreSQL container is running: `docker-compose ps`
- Check the DATABASE_URL in your .env matches docker-compose.yml

**Alembic migration error:**
```bash
# Reset the database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
python -m scripts.seed_data
```
