# Phase 4 — Part 01b: Git Ignore (.gitignore)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 01b |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.0 — Project Skeleton |
| **File** | `.gitignore` |
| **Depends On** | Part 01a (.env.example — now we protect it) |
| **Next** | [Part 01c — docker-compose.yml](./phase4-part01c-docker-compose.md) |
| **Difficulty** | 🟢 Easy |
| **Time to Type** | ~5 minutes |
| **Lines** | ~50 lines |

---

## What is .gitignore? Read This First

`.gitignore` tells Git: **"Pretend these files don't exist."** Git will never track, commit, or push them.

**Why?** Some files should NEVER go to GitHub:
- `.env` — contains your database password, API keys
- `__pycache__/` — Python bytecode (auto-generated, platform-specific)
- `node_modules/` — 200MB+ of JavaScript dependencies (download via `npm install`)
- `venv/` — your virtual environment (recreate via `pip install -r requirements.txt`)

**Real-world analogy:** It's like a "Do Not Photograph" list. Certain things in the restaurant (secret recipes, employee tax info) should never appear in marketing photos — even if they're in the building.

---

## Source Code — Line by Line

> 📁 **File:** `.gitignore`
> 📏 **Lines:** ~50
> ⏱️ **Type time:** ~5 minutes

```bash
# ============================================================================
# Health Tracker — .gitignore
# ============================================================================

# ── Python ──
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/
.eggs/
*.egg

# ── Virtual Environment ──
venv/
.venv/
env/
ENV/

# ── Environment Variables (NEVER commit secrets) ──
.env
.env.local
.env.production

# ── IDE ──
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# ── Testing ──
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover
.pytest_cache/
.mypy_cache/

# ── Node / Frontend ──
node_modules/
frontend/dist/
frontend/build/
.next/

# ── Docker ──
docker-compose.override.yml

# ── Database ──
*.db
*.sqlite3

# ── Logs ──
*.log
logs/

# ── OS ──
.DS_Store
Thumbs.db
desktop.ini

# ── SSL Certificates ──
nginx/ssl/*.pem
nginx/ssl/*.key
nginx/ssl/*.crt
```

**Line-by-line:**

- **`__pycache__/`** — Python compiles `.py` files to `.pyc` bytecode for faster loading. These are auto-generated and platform-specific (Windows bytecode ≠ Mac bytecode). Never commit.

- **`*.py[cod]`** — Matches `.pyc`, `.pyo`, `.pyd` files (compiled Python). The `[cod]` is a character class: c OR o OR d.

- **`venv/`** — Your virtual environment folder. It's 200MB+ and recreatable with `pip install -r requirements.txt`. Like `node_modules/` — always regenerate, never commit.

- **`.env`** — THE MOST IMPORTANT LINE. This file contains database passwords, API keys, JWT secrets. If committed, bots find it on GitHub within minutes.

- **`node_modules/`** — JavaScript dependencies. 500MB+. Always regenerate with `npm install`.

- **`.pytest_cache/`** — pytest stores test results for optimization. Auto-generated, no value in Git.

- **`nginx/ssl/*.pem`** — SSL certificates. Private keys MUST never be in Git.

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | .gitignore | Tells Git to ignore files matching these patterns |
| 2 | Security | .env, SSL certs, and API keys must NEVER be committed |
| 3 | Regeneratable files | venv/, node_modules/, __pycache__/ — delete and recreate anytime |
| 4 | Glob patterns | `*.py[cod]` matches .pyc, .pyo, .pyd. `**/` matches any directory depth |

---

## 🎤 Interview Q&A

### Q: "What files should never be committed to Git?"

> "Secrets (.env files, API keys, SSL private keys), generated files (\_\_pycache\_\_, node\_modules, venv — all recreatable from requirements.txt or package.json), build artifacts (dist/, build/), IDE config (.vscode/, .idea/ — personal preference), and OS files (.DS\_Store on Mac, Thumbs.db on Windows). I use a comprehensive .gitignore from day one. If a secret is ever accidentally committed, I rotate the secret immediately and use BFG Repo-Cleaner to purge it from Git history."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 01a — .env.example](./phase4-part01a-env-example.md) | | [Part 01c — docker-compose.yml](./phase4-part01c-docker-compose.md) |
