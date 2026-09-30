# Phase 0 Part 2: Environment Setup — Install Everything

| Field | Details |
|-------|---------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 0 — Project Overview & Setup |
| **Part** | 2 of 2 |
| **Previous** | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |
| **Next** | [Phase 1: System Design](./phase1-system-design.md) |
| **Time to Complete** | 2-3 hours (downloading + installing + verifying) |
| **Difficulty** | Beginner |
| **Prerequisites** | Windows 10/11, internet connection, admin access |
| **What You'll Build** | A fully configured development environment |
| **Git Commit** | N/A (no project code yet) |

---

## Table of Contents
- [Overview — What We're Installing](#overview)
- [Step 1: Python 3.11 (Backend Language)](#python)
- [Step 2: Docker Desktop (Run Databases)](#docker)
- [Step 3: Node.js 20 (Frontend Build)](#nodejs)
- [Step 4: Git (Version Control)](#git)
- [Step 5: VS Code + Extensions](#vscode)
- [Step 6: Ollama (Free Local AI)](#ollama)
- [Step 7: DBeaver (Database Client)](#dbeaver)
- [Step 8: Create Project Folder](#project-folder)
- [Step 9: Complete Verification Script](#verification)
- [Common Installation Errors (20+)](#common-errors)
- [What You Learned](#what-you-learned)
- [Next Steps](#next-steps)

---

## What You'll Learn in This Part
- How to install and configure every tool needed for the Health Tracker
- How to verify each tool works correctly
- What virtual environments are and why they matter
- How to troubleshoot 20+ common installation problems
- How to set up VS Code for Python + React development

---

<a name="overview"></a>
## Overview — What We're Installing

| # | Tool | Why We Need It | Version | Download Size |
|---|------|---------------|---------|---------------|
| 1 | **Python 3.11** | Backend language — FastAPI, SQLAlchemy, AI code | 3.11+ | ~30 MB |
| 2 | **Docker Desktop** | Run PostgreSQL, Redis, MinIO, Ollama in containers | Latest | ~500 MB |
| 3 | **Node.js 20** | Frontend build tool — React, npm, Vite | 20.x LTS | ~30 MB |
| 4 | **Git** | Version control — save snapshots, push to GitHub | 2.x | ~50 MB |
| 5 | **VS Code** | Code editor with Python + React support | Latest | ~90 MB |
| 6 | **Ollama** | Free local AI — runs Llama 3.1 on your laptop | Latest | ~100 MB (+5 GB for models) |
| 7 | **DBeaver** | Visual database client — see tables, run SQL | Latest | ~100 MB |

**Estimated total download:** ~1 GB (+ 5 GB for AI models later)

**Important:** Install in this EXACT order. Docker needs WSL2 (which might need a restart). Python needs to be installed BEFORE you create virtual environments.

---

<a name="python"></a>
## Step 1: Install Python 3.11+

### What is Python?

Python is a programming language designed for readability. It's the #1 language for AI/ML because 90% of AI libraries (PyTorch, LangChain, OpenAI SDK) are Python-first.

**Why Python 3.11 specifically?**
- Type hints with `X | None` syntax (cleaner than `Optional[X]`)
- 10-60% faster than Python 3.10
- Required by our dependencies (FastAPI, SQLAlchemy 2.0, Pydantic v2)

### Installation Steps (Windows)

1. **Go to:** https://www.python.org/downloads/
2. **Download:** Python 3.11.x or 3.12.x (click the big yellow button)
3. **Run the installer:**

```
┌─────────────────────────────────────────────────────────────┐
│              CRITICAL CHECKBOX — DO NOT MISS!                 │
│                                                               │
│  On the VERY FIRST screen of the installer:                  │
│                                                               │
│  ☑ Add Python 3.11 to PATH    ← CHECK THIS!!!               │
│  ☐ Install for all users                                     │
│                                                               │
│  If you miss this, Python won't work from the terminal.      │
│  You'd have to uninstall and reinstall.                      │
│                                                               │
│  Then click "Install Now" (not "Customize installation")     │
└─────────────────────────────────────────────────────────────┘
```

4. Wait for installation to complete
5. Click "Disable path length limit" if offered (optional but recommended)
6. Click "Close"

### Verify Installation

**Close ALL terminal/PowerShell windows** and open a NEW one:

```powershell
python --version
```

**Expected output:**
```
Python 3.11.9
```
(or 3.12.x — any 3.11+ is fine)

Also verify pip (Python's package installer):
```powershell
pip --version
```

**Expected:**
```
pip 24.0 from C:\Users\...\Python311\Lib\site-packages\pip (python 3.11)
```

### What is pip?

pip = **P**ackage **I**nstaller for **P**ython. Like npm for Node.js or Maven for Java.

```powershell
pip install fastapi    # Downloads and installs FastAPI from the internet
pip install -r requirements.txt    # Install ALL packages listed in a file
pip list               # Show all installed packages
pip uninstall fastapi  # Remove a package
```

### What is a Virtual Environment?

**The Problem:** You have two Python projects. Project A needs `fastapi==0.115.0`. Project B needs `fastapi==0.110.0`. They CAN'T both use the same Python installation — version conflict!

**The Solution:** A virtual environment is a **separate folder** with its own Python and packages. Each project gets its own isolated environment.

```
Without venv:
  C:\Python311\Lib\site-packages\     ← ALL projects share this
  fastapi==0.115.0                     ← What if Project B needs 0.110?

With venv:
  health-tracker\venv\Lib\site-packages\     ← Project A's packages
  fastapi==0.115.0

  other-project\venv\Lib\site-packages\      ← Project B's packages
  fastapi==0.110.0
```

**Real-world analogy:** A virtual environment is like giving each project its own kitchen. Project A's chef uses ingredient version X, Project B's chef uses version Y — they never conflict because they have separate kitchens.

### How to Create and Use a Virtual Environment

```powershell
# Navigate to your project folder
cd C:\Users\YourName\Documents\health-tracker\backend

# Create the virtual environment (one time only)
python -m venv venv
# This creates a "venv" folder with its own Python + pip

# Activate it (EVERY TIME you open a new terminal)
# Windows PowerShell:
venv\Scripts\activate

# You'll see "(venv)" at the start of your prompt:
(venv) PS C:\Users\YourName\Documents\health-tracker\backend>

# Now pip installs go to THIS project's venv folder only
pip install fastapi    # Goes to venv\Lib\site-packages\, NOT system Python

# When done working, deactivate:
deactivate
```

**CRITICAL RULE:** Always activate venv before running ANY Python command for this project. If you don't see `(venv)` in your prompt, your commands use the SYSTEM Python (wrong!).

### Troubleshooting Python

| Problem | Cause | Fix |
|---------|-------|-----|
| `'python' is not recognized` | Python not in PATH | Reinstall with "Add to PATH" checked |
| `python --version` shows 2.7 | Old Python 2 installed | Use `python3 --version` or uninstall Python 2 |
| `pip install` fails with permission error | Not using venv, or PowerShell not admin | Activate venv first, or run as Administrator |
| `venv\Scripts\activate` says "cannot be loaded" | PowerShell execution policy blocks scripts | Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `ModuleNotFoundError: No module named 'venv'` | Python installed without venv module | Reinstall Python with full installation (not minimal) |

---

<a name="docker"></a>
## Step 2: Install Docker Desktop

### What is Docker?

Docker runs applications in **containers** — lightweight, isolated environments with their own OS, libraries, and files. Instead of installing PostgreSQL on your laptop (and dealing with version conflicts, port conflicts, and uninstall headaches), you run it in a container:

```powershell
# Without Docker (painful):
# 1. Download PostgreSQL installer (200MB)
# 2. Run installer, choose options, set password
# 3. It installs system-wide (conflicts with other versions)
# 4. Uninstalling doesn't clean everything up

# With Docker (one command):
docker-compose up postgres -d
# PostgreSQL 16 with pgvector is running on localhost:5432. Done.
# To stop and clean up: docker-compose down
```

**Real-world analogy:** Docker is like a food truck. A restaurant needs plumbing, electricity, building permits. A food truck carries everything it needs — you just park it and start cooking. Docker containers carry everything the app needs — you just "start" them.

### Prerequisites: Enable WSL 2

Docker Desktop on Windows requires **WSL 2** (Windows Subsystem for Linux) — a mini Linux running inside Windows.

```powershell
# Open PowerShell as Administrator (Right-click → "Run as Administrator")
wsl --install
```

**This may restart your computer.** After restart:

```powershell
# Verify WSL 2 is installed
wsl --status
```

**Expected:** Should mention "Default Version: 2"

If you see errors about virtualization:
```
┌─────────────────────────────────────────────────────────────┐
│  IF YOU SEE: "Virtualization is disabled in the firmware"    │
│                                                               │
│  This means your BIOS has virtualization turned off.         │
│  Fix:                                                         │
│  1. Restart your computer                                    │
│  2. Press F2 / F12 / Delete during startup to enter BIOS    │
│  3. Find "Intel VT-x" or "AMD-V" setting                    │
│  4. Enable it                                                │
│  5. Save and exit BIOS                                       │
│  6. Windows will restart                                     │
│  7. Run "wsl --install" again                                │
│                                                               │
│  The exact BIOS key varies by laptop brand:                  │
│  Dell: F2 | HP: F10 | Lenovo: F1 | Asus: F2 | Acer: F2    │
└─────────────────────────────────────────────────────────────┘
```

### Installation Steps

1. **Go to:** https://www.docker.com/products/docker-desktop/
2. **Download:** Docker Desktop for Windows
3. **Run installer:**
   - ✅ "Use WSL 2 instead of Hyper-V" — keep checked
   - Click OK → Install → Close
4. **Restart** your computer
5. **Open Docker Desktop** from Start Menu
   - Accept the terms
   - **Skip** the tutorial/sign-in (you don't need a Docker Hub account)
   - Wait until the Docker whale icon in the system tray shows "Docker Desktop is running" (green)

### Verify Installation

```powershell
docker --version
```
**Expected:** `Docker version 27.x.x, build ...`

```powershell
docker compose version
```
**Expected:** `Docker Compose version v2.x.x`

**Test it works:**
```powershell
docker run hello-world
```
**Expected:** Pulls a small image and prints "Hello from Docker! This message shows that your installation appears to be working correctly."

### Docker Key Concepts

| Concept | What It Is | Analogy |
|---------|-----------|---------|
| **Image** | A read-only template with OS + software | A frozen meal kit (everything pre-packaged) |
| **Container** | A running instance of an image | The meal being cooked (from the frozen kit) |
| **Volume** | Persistent storage that survives container restarts | Your fridge — data stays even when you turn off the stove |
| **Docker Compose** | YAML file that defines and runs MULTIPLE containers | A dinner party plan — "start the oven, fridge, and dishwasher together" |
| **Port mapping** | `5432:5432` = laptop port : container port | Your apartment number → room number inside the apartment |

### Troubleshooting Docker

| Problem | Cause | Fix |
|---------|-------|-----|
| "WSL 2 installation is incomplete" | WSL not installed | Run `wsl --install` as admin, restart |
| "Hardware assisted virtualization disabled" | VT-x/AMD-V off in BIOS | Enter BIOS (F2/F10/F12), enable virtualization |
| Docker Desktop won't start | Background service not running | Restart PC, or run `net start com.docker.service` as admin |
| "Cannot connect to the Docker daemon" | Docker Desktop not started | Open Docker Desktop app, wait for whale icon to turn green |
| Docker is very slow | WSL 2 using too much RAM | Create `C:\Users\YourName\.wslconfig` with `[wsl2]\nmemory=4GB` |
| `port is already allocated` | Something else using that port | Run `netstat -ano | findstr :5432` to find the process |

---

<a name="nodejs"></a>
## Step 3: Install Node.js 20

### What is Node.js?

Node.js is a **JavaScript runtime** — it lets you run JavaScript outside the browser. We need it for:
- **React** (frontend framework)
- **npm** (package manager — like pip but for JavaScript)
- **Vite** (frontend build tool — instant hot reload)

**We only use Node.js for the FRONTEND.** The backend is 100% Python.

### Installation Steps

1. **Go to:** https://nodejs.org/
2. **Download:** the **LTS** version (should be 20.x — big green button)
3. **Run installer:**
   - Accept license
   - Default install location is fine
   - ✅ "Automatically install necessary tools" — check this if shown
   - Click Install → Finish

### Verify Installation

```powershell
node --version
```
**Expected:** `v20.x.x` (any 20.x is fine)

```powershell
npm --version
```
**Expected:** `10.x.x`

### What is npm?

npm = **N**ode **P**ackage **M**anager. Downloads JavaScript libraries.

```powershell
npm install react           # Install one package
npm install                 # Install ALL packages from package.json
npm run dev                 # Run the "dev" script (starts Vite dev server)
npm run build               # Create production build
```

**npm vs pip comparison:**

| Python (pip) | JavaScript (npm) |
|-------------|------------------|
| `pip install fastapi` | `npm install react` |
| `pip install -r requirements.txt` | `npm install` (reads package.json) |
| `pip list` | `npm list` |
| `venv/` folder | `node_modules/` folder |
| `requirements.txt` | `package.json` |

### Troubleshooting Node.js

| Problem | Cause | Fix |
|---------|-------|-----|
| `'node' is not recognized` | Not in PATH | Restart PowerShell. If still fails, reinstall |
| Shows Node 16 or 18 | Old version installed | Uninstall old version first, then install 20 |
| `npm ERR! EACCES permission denied` | Permission issue | Run PowerShell as Administrator |

---

<a name="git"></a>
## Step 4: Install Git

### What is Git?

Git is a **version control system** — it saves snapshots (called "commits") of your code. If you break something, you can go back to a working version.

**Real-world analogy:** Git is like "Save As" for your entire project folder. You can have "version_monday", "version_after_fixing_bug", "version_before_experiment" — and switch between them instantly.

### Installation Steps

1. **Go to:** https://git-scm.com/download/win
2. **Download:** 64-bit installer
3. **Run installer — use these options:**
   - "Choosing the default editor" → select **Notepad** or **VS Code** (NOT Vim!)
   - "Adjusting your PATH" → "Git from the command line and also from 3rd-party software" ✅
   - Everything else: click Next → Install → Finish

### Configure Git (Required — Do This Now)

```powershell
# Set your name (appears in every commit)
git config --global user.name "Shreya"

# Set your email (must match your GitHub email later)
git config --global user.email "shreya@example.com"

# Set default branch name to 'main'
git config --global init.defaultBranch main

# Verify
git config --list
```

### Verify Installation

```powershell
git --version
```
**Expected:** `git version 2.45.x.windows.x`

### Git Key Commands (Preview)

| Command | What It Does |
|---------|-------------|
| `git init` | Initialize a new Git repository in current folder |
| `git add .` | Stage ALL changed files for the next commit |
| `git commit -m "message"` | Save a snapshot with a description |
| `git status` | Show which files have changed since last commit |
| `git log --oneline` | Show commit history (one line per commit) |
| `git push origin main` | Upload commits to GitHub |
| `git pull origin main` | Download latest commits from GitHub |

---

<a name="vscode"></a>
## Step 5: Install VS Code + Extensions

### What is VS Code?

Visual Studio Code is a **code editor** — like Notepad but with superpowers: syntax highlighting, auto-complete, debugging, integrated terminal, Git integration, and thousands of extensions.

### Installation Steps

1. **Go to:** https://code.visualstudio.com/
2. **Download and install** with defaults
3. Open VS Code

### Install These Extensions

Open VS Code → click the Extensions icon (⬜ on the left sidebar, or Ctrl+Shift+X) → search and install:

| Extension | Publisher | Why |
|-----------|----------|-----|
| **Python** | Microsoft | Python language support, debugging, IntelliSense |
| **Pylance** | Microsoft | Fast type checking, auto-complete for Python |
| **ES7+ React/Redux/React-Native snippets** | dsznajder | React component shortcuts |
| **Tailwind CSS IntelliSense** | Tailwind Labs | Tailwind class auto-complete |
| **Docker** | Microsoft | Docker file syntax highlighting |
| **Thunder Client** | Ranga Vadhineni | Test API endpoints (like Postman, inside VS Code) |
| **GitLens** | GitKraken | See who changed each line and when |
| **Prettier** | Prettier | Auto-format JavaScript/TypeScript on save |

### Configure VS Code for Python

1. Open VS Code
2. Press `Ctrl+Shift+P` → type "Python: Select Interpreter"
3. Select the one from your virtual environment: `.\venv\Scripts\python.exe`
4. Press `Ctrl+,` (Settings) → search "Format On Save" → ✅ Enable it

---

<a name="ollama"></a>
## Step 6: Install Ollama (Free Local AI)

### What is Ollama?

Ollama lets you run **AI models on your own laptop** — no API key, no internet, no cost. It downloads open-source models (Llama 3.1, Mistral, etc.) and runs them locally.

**Why we need it:** Our AI module needs an LLM (Large Language Model) to generate responses. During development, we use Ollama (free) instead of OpenAI ($$$).

### Installation Steps

1. **Go to:** https://ollama.com/download
2. **Download:** Windows installer
3. **Install:** run the installer, accept defaults
4. Ollama starts automatically as a background service

### Verify Installation

```powershell
ollama --version
```
**Expected:** `ollama version 0.x.x`

### Download AI Models (Later — After Docker Is Running)

We'll download models after setting up the project. For now, just verify Ollama is installed. When you're ready:

```powershell
# Download the chat model (~4.7 GB, takes 5-15 minutes on fast internet)
ollama pull llama3.1:8b

# Download the embedding model (~274 MB, takes 1-2 minutes)
ollama pull nomic-embed-text

# Verify models are downloaded
ollama list
```

**Expected output after pulling both:**
```
NAME                    SIZE
llama3.1:8b             4.7 GB
nomic-embed-text        274 MB
```

### Minimum Requirements for Ollama

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| RAM | 8 GB | 16 GB |
| Disk Space | 6 GB (for models) | 10 GB |
| CPU | Any modern CPU | 4+ cores for decent speed |
| GPU | Not required (CPU works) | NVIDIA GPU (5x faster) |

**If your laptop has < 8 GB RAM:** Skip Ollama. Use Groq (free cloud API) instead. Just set `LLM_PROVIDER=groq` in your `.env` file and get a free API key from https://console.groq.com

### Troubleshooting Ollama

| Problem | Cause | Fix |
|---------|-------|-----|
| `ollama` command not found | Not installed or not in PATH | Restart PowerShell. Reinstall if needed |
| Model download fails | Not enough disk space | Free up 6+ GB of disk space |
| Model runs very slowly | Not enough RAM | Close other apps. Or use `LLM_PROVIDER=groq` instead |
| Port 11434 already in use | Another Ollama instance | `taskkill /F /IM ollama.exe` then restart |

---

<a name="dbeaver"></a>
## Step 7: Install DBeaver (Database Client)

### What is DBeaver?

DBeaver is a **visual database tool**. Instead of writing SQL in a terminal, you can:
- Browse tables with a UI (like Excel)
- Run SQL queries with auto-complete
- See relationships between tables
- Export data as CSV

### Installation Steps

1. **Go to:** https://dbeaver.io/download/
2. **Download:** Windows Installer (64-bit) — Community Edition (free)
3. **Install:** click Next through everything, defaults are fine

### How to Connect (After Docker Is Running)

Once you start the project's Docker containers (in Phase 4), connect DBeaver:

1. Open DBeaver → File → New → Database Connection
2. Select **PostgreSQL** → Next
3. Fill in:
   - Host: `localhost`
   - Port: `5432`
   - Database: `healthtracker`
   - Username: `healthuser`
   - Password: `healthpass`
4. Click "Test Connection" → if it shows "Connected" → click Finish
5. You can now browse tables, run queries, see data

**Note:** Don't try to connect yet — PostgreSQL isn't running. We'll start it in Phase 4 Part 01.

---

<a name="project-folder"></a>
## Step 8: Create the Project Folder

```powershell
# Navigate to your Documents folder (or wherever you keep projects)
cd C:\Users\YourName\Documents

# Create the project folder
mkdir health-tracker
cd health-tracker

# Initialize Git
git init

# Verify
git status
# Expected: "On branch main / No commits yet / nothing to commit"

# You should now be in:
# C:\Users\YourName\Documents\health-tracker\
```

---

<a name="verification"></a>
## Step 9: Complete Verification Script

Run each command below. ALL must pass before moving to Phase 1.

```powershell
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Health Tracker — Environment Check" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
$py = python --version 2>&1
if ($py -match "3\.1[1-9]") { Write-Host "  ✅ Python — $py" -ForegroundColor Green }
else { Write-Host "  ❌ Python — NEED 3.11+" -ForegroundColor Red }

# Check pip
$pip = pip --version 2>&1
if ($pip -match "pip") { Write-Host "  ✅ pip — installed" -ForegroundColor Green }
else { Write-Host "  ❌ pip — NOT FOUND" -ForegroundColor Red }

# Check Docker
$docker = docker --version 2>&1
if ($docker -match "Docker") { Write-Host "  ✅ Docker — $docker" -ForegroundColor Green }
else { Write-Host "  ❌ Docker — NOT FOUND" -ForegroundColor Red }

# Check Docker Compose
$compose = docker compose version 2>&1
if ($compose -match "v2") { Write-Host "  ✅ Docker Compose — $compose" -ForegroundColor Green }
else { Write-Host "  ❌ Docker Compose — NOT FOUND" -ForegroundColor Red }

# Check Node.js
$node = node --version 2>&1
if ($node -match "v2[0-9]") { Write-Host "  ✅ Node.js — $node" -ForegroundColor Green }
else { Write-Host "  ❌ Node.js — NEED v20+" -ForegroundColor Red }

# Check npm
$npm = npm --version 2>&1
if ($npm -match "10") { Write-Host "  ✅ npm — $npm" -ForegroundColor Green }
else { Write-Host "  ❌ npm — NOT FOUND" -ForegroundColor Red }

# Check Git
$git = git --version 2>&1
if ($git -match "git version") { Write-Host "  ✅ Git — $git" -ForegroundColor Green }
else { Write-Host "  ❌ Git — NOT FOUND" -ForegroundColor Red }

# Check Ollama
$ollama = ollama --version 2>&1
if ($ollama -match "ollama") { Write-Host "  ✅ Ollama — $ollama" -ForegroundColor Green }
else { Write-Host "  ⚠️  Ollama — not found (optional, can use Groq instead)" -ForegroundColor Yellow }

# Check Docker daemon
try {
    docker info 2>&1 | Out-Null
    Write-Host "  ✅ Docker daemon — running" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker daemon — NOT running (open Docker Desktop)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  If all green: you're ready for Phase 1!" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""
```

Copy-paste this into PowerShell and run it. You should see all green checkmarks.

---

<a name="common-errors"></a>
## Common Installation Errors & Fixes (20+)

### Python Errors

| # | Error | Cause | Fix |
|---|-------|-------|-----|
| 1 | `'python' is not recognized` | Python not in PATH | Reinstall, CHECK "Add to PATH" |
| 2 | `python --version` shows 3.9 | Old Python installed | Uninstall old, install 3.11+ |
| 3 | `pip install` permission error | Not in virtual environment | Activate venv: `venv\Scripts\activate` |
| 4 | `Cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| 5 | `No module named 'venv'` | Minimal Python install | Reinstall Python with "full" option |

### Docker Errors

| # | Error | Cause | Fix |
|---|-------|-------|-----|
| 6 | "WSL 2 installation is incomplete" | WSL not installed | `wsl --install` as admin, restart |
| 7 | "Hardware assisted virtualization disabled" | VT-x/AMD-V off in BIOS | Enter BIOS, enable virtualization |
| 8 | Docker Desktop won't start | Service not running | Restart PC, or `net start com.docker.service` |
| 9 | "Cannot connect to the Docker daemon" | Docker Desktop not open | Open Docker Desktop, wait for green whale |
| 10 | Very slow first startup | Normal | First launch takes 2-3 minutes. Be patient. |
| 11 | `port is already allocated` | Port already in use | `netstat -ano \| findstr :5432` → find and kill the process |

### Node.js Errors

| # | Error | Cause | Fix |
|---|-------|-------|-----|
| 12 | `'node' is not recognized` | Not in PATH | Restart PowerShell |
| 13 | Old Node version (16, 18) | Old installation | Uninstall old, install 20 LTS |
| 14 | `npm ERR! EACCES` | Permission issue | Run as Administrator |

### Git Errors

| # | Error | Cause | Fix |
|---|-------|-------|-----|
| 15 | `'git' is not recognized` | Not in PATH | Reinstall, check "Git from command line" |
| 16 | `fatal: not a git repository` | Not in a git-initialized folder | Run `git init` first |
| 17 | SSH connection refused (push to GitHub) | Corporate firewall blocks SSH | Use HTTPS URL: `git remote set-url origin https://github.com/...` |

### Ollama Errors

| # | Error | Cause | Fix |
|---|-------|-------|-----|
| 18 | Model download stuck | Slow internet / not enough disk | Free 6+ GB, check internet, retry |
| 19 | Model runs extremely slow | < 8 GB RAM | Close other apps, or use `LLM_PROVIDER=groq` |
| 20 | Port 11434 in use | Duplicate Ollama process | `taskkill /F /IM ollama.exe` then restart |

### General

| # | Error | Cause | Fix |
|---|-------|-------|-----|
| 21 | VS Code "Python not found" | Wrong interpreter selected | Ctrl+Shift+P → "Python: Select Interpreter" → choose venv |
| 22 | Corporate proxy blocks downloads | Company firewall | Ask IT for proxy settings, or use mobile hotspot for downloads |
| 23 | Antivirus blocks installer | False positive | Temporarily disable antivirus, install, re-enable |
| 24 | "This app can't run on your PC" | 32-bit Windows or ARM | You need 64-bit Windows 10/11 |

---

<a name="what-you-learned"></a>
## What You Learned

| # | Concept | What You Practiced |
|---|---------|-------------------|
| 1 | **Python + pip** | Installed language runtime + package manager |
| 2 | **Virtual environments** | Isolated project dependencies (venv) |
| 3 | **Docker + WSL 2** | Container runtime for databases and services |
| 4 | **Docker concepts** | Images, containers, volumes, port mapping |
| 5 | **Node.js + npm** | JavaScript runtime for React frontend |
| 6 | **Git configuration** | Global name/email, default branch |
| 7 | **VS Code extensions** | Python, Tailwind, Docker, Thunder Client |
| 8 | **Ollama** | Local AI model runner (free alternative to OpenAI) |
| 9 | **DBeaver** | Visual database client for PostgreSQL |
| 10 | **Environment verification** | PowerShell script to validate setup |
| 11 | **PATH variable** | How Windows finds executables |
| 12 | **Troubleshooting** | 24 common errors and their fixes |

---

<a name="next-steps"></a>
## Next Steps

**What's coming in Phase 1 (System Design):**
- Define all functional and non-functional requirements
- Make 10+ design decisions (with alternatives and trade-offs) in boxed format
- Design all 38 API endpoints with request/response examples
- Design all 8 database tables with full CREATE TABLE SQL
- Capacity planning with back-of-envelope math
- AI pipeline design (LLM + RAG + Agent + Workflow)
- Security design (JWT, bcrypt, rate limiting)

**Before moving on, verify:**
- [ ] All tools show green ✅ in the verification script
- [ ] Docker Desktop is running (green whale icon)
- [ ] You can create and activate a Python virtual environment
- [ ] You understand the difference between pip and npm
- [ ] You understand what Docker containers and images are
- [ ] You have the `health-tracker/` folder with Git initialized

---

## Document Index

| Phase | Part | Document | Status |
|-------|------|----------|--------|
| 0 | 1 | [Project Overview](./phase0-part1-project-overview.md) | ✅ Complete |
| 0 | **2** | **Environment Setup** | ← You are here |
| 1 | - | [System Design](./phase1-system-design.md) | ⬜ Next |
| 2 | - | [High-Level Design](./phase2-high-level-design.md) | ⬜ |
| 3 | - | [Low-Level Design](./phase3-low-level-design.md) | ⬜ |
| 4 | 01 | [Project Setup + Docker](./phase4-part01-project-setup-docker.md) | ⬜ |
| ... | ... | ... | ... |

---
*End of Phase 0 Part 2 — Environment Setup*
*Next: [Phase 1 — System Design](./phase1-system-design.md)*
