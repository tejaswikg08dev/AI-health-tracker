# 💻 Phase 0 — Part 04: Environment Setup

> **"Before you write a single line of code, set up your tools. A carpenter sharpens the axe before cutting the tree."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 0 — Overview & Setup |
| **Part** | 04 of 05 |
| **Previous** | [Part 03 — Tech Stack Explained](./phase0-part03-tech-stack-explained.md) |
| **Next** | [Part 05 — AI Concepts from Zero](./phase0-part05-ai-concepts-from-zero.md) |
| **Time to Complete** | ~45 minutes (includes downloads) |

---

## What You Need to Install

| Tool | Version | Why | Download |
|------|---------|-----|----------|
| **Python** | 3.11+ | Backend language | [python.org/downloads](https://www.python.org/downloads/) |
| **Docker Desktop** | Latest | Runs PostgreSQL, Redis, etc. | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **Node.js** | 20+ | Frontend build tool | [nodejs.org](https://nodejs.org/) |
| **Git** | Latest | Version control | [git-scm.com](https://git-scm.com/) |
| **VS Code** | Latest | Code editor | [code.visualstudio.com](https://code.visualstudio.com/) |

---

## Step 1: Install Python 3.11+

### Windows
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.11 or 3.12
3. **IMPORTANT:** Check ✅ "Add Python to PATH" during installation
4. Open PowerShell and verify:

```powershell
python --version
# Expected: Python 3.11.x or 3.12.x

pip --version
# Expected: pip 24.x from ...
```

### What is pip?
pip = Package Installer for Python. Like npm for Node.js. You run `pip install fastapi` to install packages.

### What is a Virtual Environment?
A virtual environment is a **separate folder** with its own Python packages. Without it, all projects share the same packages — Project A needs fastapi==0.115.0, Project B needs fastapi==0.110.0 → conflict!

```powershell
# Create a virtual environment (do this ONCE per project)
python -m venv venv

# Activate it (do this EVERY TIME you open a terminal)
# Windows PowerShell:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Your prompt changes to show (venv):
(venv) PS C:\health-tracker\backend>

# Now pip install goes into THIS project's folder only
pip install fastapi
# Installed to: venv\lib\python3.11\site-packages\fastapi\

# Deactivate when done
deactivate
```

---

## Step 2: Install Docker Desktop

1. Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Install and restart your computer
3. Open Docker Desktop — wait for it to start (whale icon in taskbar)
4. Verify:

```powershell
docker --version
# Expected: Docker version 24.x or 25.x

docker-compose --version
# Expected: Docker Compose version v2.x

# Test it works:
docker run hello-world
# Expected: "Hello from Docker!"
```

### What is Docker?
Docker runs applications in **containers** — isolated environments with their own OS, libraries, and files. Instead of installing PostgreSQL on your laptop (and dealing with version conflicts), you run it in a container.

```powershell
# This starts PostgreSQL without installing it on your system:
docker run -d --name test-postgres -e POSTGRES_PASSWORD=test -p 5432:5432 postgres:16
# PostgreSQL is now running on localhost:5432

# Stop and remove when done:
docker stop test-postgres && docker rm test-postgres
```

---

## Step 3: Install Node.js 20+

1. Download from [nodejs.org](https://nodejs.org/) (LTS version)
2. Install with defaults
3. Verify:

```powershell
node --version
# Expected: v20.x.x

npm --version
# Expected: 10.x.x
```

### What is Node.js and npm?
- **Node.js** = JavaScript runtime (runs JS outside the browser)
- **npm** = Node Package Manager (like pip for JavaScript)
- We need these for the React frontend ONLY (backend is Python)

---

## Step 4: Install Git

1. Download from [git-scm.com](https://git-scm.com/)
2. Install with defaults (choose "Git from the command line" option)
3. Verify:

```powershell
git --version
# Expected: git version 2.x.x

# Configure your identity (one time):
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

---

## Step 5: VS Code Extensions

Install these VS Code extensions for the best experience:

| Extension | What It Does |
|-----------|-------------|
| **Python** (Microsoft) | Python language support, debugging |
| **Pylance** (Microsoft) | Fast Python type checking |
| **ES7+ React/Redux/React-Native** | React snippets |
| **Tailwind CSS IntelliSense** | Tailwind class autocomplete |
| **Docker** (Microsoft) | Docker file support |
| **Thunder Client** | API testing (like Postman, but in VS Code) |

---

## Step 6: Create the Project Folder

```powershell
# Navigate to your workspace
cd C:\Users\YourName\Documents

# Create the project folder
mkdir health-tracker
cd health-tracker

# Initialize git
git init

# Create the folder structure for the backend
mkdir backend
cd backend
mkdir app
cd ..

# You should now be in:
# C:\Users\YourName\Documents\health-tracker\
```

---

## ✅ Verification Checklist

Run each command. If ALL pass, you're ready to start coding:

```powershell
python --version          # Python 3.11+
pip --version             # pip 24+
docker --version          # Docker 24+
docker-compose --version  # Compose v2+
node --version            # Node 20+
npm --version             # npm 10+
git --version             # git 2+
```

---

## 🎤 Interview Q&A

### Q: "How do you set up a Python development environment?"

> "I use virtual environments to isolate project dependencies. `python -m venv venv` creates an isolated Python installation, `source venv/bin/activate` activates it, and `pip install -r requirements.txt` installs pinned dependencies. For infrastructure services like PostgreSQL and Redis, I use Docker Compose so every developer gets the exact same versions without manual installation. I also use ruff for linting and mypy for type checking, configured in pyproject.toml."

### Q: "Why virtual environments?"

> "Without a virtual environment, all Python projects share the same package versions. If Project A needs fastapi 0.115 and Project B needs 0.110, they conflict. A virtual environment gives each project its own `site-packages` folder — complete isolation. It's the Python equivalent of Node.js `node_modules`."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03 — Tech Stack](./phase0-part03-tech-stack-explained.md) | | [Part 05 — AI Concepts](./phase0-part05-ai-concepts-from-zero.md) |
