# 🔔 Phase 4 Part 13: Notifications Module — Overview & Roadmap

> **"Notifications are the nudge that keeps users engaged. A reminder at 8 PM: 'You haven't logged 3 habits today!' A celebration at 30 days: '🔥 30-day Water streak!' These small touches make the difference between a used app and an abandoned one."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 13 (Notifications Module — Overview) |
| **Sprint** | Sprint 4 — Delivery + Lambda |
| **Release** | Release 4.1 — Notifications & Email |
| **Previous** | [phase4-part12c-ai-migration.md](./phase4-part12c-ai-migration.md) |
| **Next** | [phase4-part13a-notifications-models-schemas-email-provider.md](./phase4-part13a-notifications-models-schemas-email-provider.md) |
| **Module Files** | 7 Python files + 4 HTML email templates + 1 Alembic migration |
| **Endpoints** | 3 (get settings, update settings, send test email) |
| **Sub-Parts** | 4 documents (13a–13d) |
| **Difficulty** | Medium (Strategy pattern for email, Jinja2 HTML templates, scheduled tasks, per-user preferences) |

---

## 📖 Table of Contents

1. [What Is the Notifications Module?](#what-is-notifications)
2. [The 4 Notification Types](#notification-types)
3. [Email Provider Strategy Pattern (Again!)](#email-strategy)
4. [Endpoints Overview](#endpoints)
5. [File List & Build Order](#file-list)
6. [Sub-Part Roadmap](#roadmap)
7. [Architecture Diagram](#architecture)
8. [Key Concepts You'll Learn](#concepts)
9. [Design Decisions](#design-decisions)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="what-is-notifications"></a>
## 1. What Is the Notifications Module?

The Notifications module handles **proactive outreach** — reaching out to users before they ask. While every other module waits for the user to make a request, Notifications initiates contact.

### Real-World Analogy

Think of a **fitness app with a personal trainer**:
- **Auth/Habits/Logs** = the gym equipment (user goes to it)
- **Analytics/AI** = the trainer's analysis (user asks for it)
- **Notifications** = the trainer texting you: "Hey! You missed leg day. Your streak is at risk. Also, congrats on 30 days of running! 🎉"

Without notifications, users forget to log → streaks break → they lose motivation → they stop using the app. With notifications, a gentle nudge at the right time keeps the habit loop alive.

### Module Features

| Feature | What It Does | When It Fires |
|---------|-------------|--------------|
| **Daily Reminder** | "You haven't logged 3 habits today!" | Daily at user's preferred time |
| **Streak Milestone** | "🔥 30-day streak on Water Intake!" | When streak hits 7, 14, 30, 60, 90, 365 days |
| **Weekly Report Alert** | "Your weekly report is ready!" | After AI generates the report (Part 11) |
| **Export Ready** | "Your CSV export is ready to download" | After export file is generated (Part 14) |

---

<a name="notification-types"></a>
## 2. The 4 Notification Types

### 1. Daily Reminder

```
📧 TO: shreya@test.com
SUBJECT: 🏥 Time to log your habits — September 26, 2026

Hi Shreya! 👋

You've logged 3 of 6 habits today.
Missing: Exercise, Meditation, Steps

[Log Now →]
```

**When:** Daily at `reminder_time` (default 08:00 PM, configurable per user)
**Skip if:** User already logged all habits today
**Trigger:** Lambda/Celery scheduled task

### 2. Streak Milestone

```
📧 TO: shreya@test.com
SUBJECT: 🔥 30-Day Streak on Water Intake!

Hi Shreya! 🎉

AMAZING! You've logged Water Intake for 30 consecutive days!
That's consistency and dedication. Keep it going!

Your longest streak ever: 30 days (and counting!)

[See Your Streaks →]
```

**When:** Streak hits a milestone: 7, 14, 21, 30, 60, 90, 100, 180, 365 days
**Trigger:** Daily check (Lambda) or event-driven (after log creation)

### 3. Weekly Report Alert

```
📧 TO: shreya@test.com
SUBJECT: 📊 Your Weekly Health Report — Sep 20 to Sep 26

Hi Shreya!

Your AI-generated weekly health report is ready!

Quick peek:
• 6 habits tracked, 78% completion
• Best streak: Water Intake — 15 days! 💧
• AI insight: "Your mood is higher on exercise days"

[Read Full Report →]
```

**When:** After the weekly report workflow (Part 11) completes
**Trigger:** Called by `generate_weekly_report()` in AI Service

### 4. Export Ready

```
📧 TO: shreya@test.com
SUBJECT: 📁 Your Health Tracker Export is Ready

Your CSV export (Sep 1 – Sep 30) is ready to download!

[Download CSV →]
```

**When:** After CSV/PDF generation completes (Part 14)
**Trigger:** Called by Export Service

---

<a name="email-strategy"></a>
## 3. Email Provider Strategy Pattern (Again!)

Same pattern as LLM providers (Part 08) — abstract interface, multiple implementations, factory function:

```
┌──────────────────────────┐
│  BaseEmailProvider       │ ← Abstract: send(to, subject, html)
│  (abc.ABC)               │
├──────────────────────────┤
│  + send() → bool         │ ← Returns True/False (never crashes)
└──────────┬───────────────┘
           │ implements
    ┌──────┼──────────────────────────┐
    │      │                          │
┌───▼────┐ ┌──▼──────┐ ┌─────────────▼──┐
│Console │ │ Resend  │ │   AWS SES      │
│Provider│ │ Provider│ │   Provider     │
│        │ │         │ │                │
│ Prints │ │ Free    │ │ Production     │
│ to     │ │ 100/day │ │ 3K/month free  │
│ terminal│ │ API     │ │ from EC2       │
└────────┘ └─────────┘ └────────────────┘

Factory: get_email_provider()
  → reads EMAIL_PROVIDER from config
  → returns Console, Resend, or SES
```

**Same principle as LLM providers:**
- Development: `EMAIL_PROVIDER=console` → prints to terminal, $0
- Staging: `EMAIL_PROVIDER=resend` → Resend.com free tier (100 emails/day)
- Production: `EMAIL_PROVIDER=ses` → AWS SES (3K emails/month free from EC2)

One env var change. Zero code changes.

---

<a name="endpoints"></a>
## 4. Endpoints Overview

| # | Method | Endpoint | Auth | Request Body | Response | What It Does |
|---|--------|----------|:----:|-------------|----------|-------------|
| 1 | `GET` | `/notifications/settings` | ✅ | — | `NotificationSettingsResponse` | Get current preferences |
| 2 | `PUT` | `/notifications/settings` | ✅ | `NotificationSettingsUpdate` | `NotificationSettingsResponse` | Update preferences |
| 3 | `POST` | `/notifications/test-email` | ✅ | `TestEmailRequest` | `SuccessResponse` | Send a test email |

### Notification Settings Schema

```json
{
    "id": "uuid",
    "daily_reminder": true,
    "weekly_report": true,
    "streak_alerts": true,
    "reminder_time": "20:00",
    "created_at": "2026-09-26T10:00:00Z"
}
```

Each toggle can be independently on/off. `reminder_time` is in `HH:MM` format (user's local time).

---

<a name="file-list"></a>
## 5. File List & Build Order

### Module File Structure

```
backend/app/modules/notifications/
├── __init__.py
├── models.py             ← NotificationSettings table (1 row per user)
├── schemas.py            ← Settings response, update, test-email request
├── email_provider.py     ← Abstract + 3 implementations + factory
├── service.py            ← Settings CRUD + 4 email-sending methods
├── tasks.py              ← Celery tasks (scheduled background jobs)
├── router.py             ← 3 endpoints
└── templates/            ← 4 HTML email templates (Jinja2)
    ├── daily_reminder.html
    ├── weekly_report.html
    ├── streak_milestone.html
    └── export_ready.html

backend/alembic/versions/
└── 005_create_notification_settings.py
```

### Build Order

| # | File | Why This Order |
|---|------|---------------|
| 1 | `models.py` | Table must exist first |
| 2 | `schemas.py` | Router uses for validation |
| 3 | `005_migration.py` | Creates the table |
| 4 | `email_provider.py` | Service uses for sending |
| 5 | `templates/` | Service renders these |
| 6 | `service.py` | Business logic + email sending |
| 7 | `tasks.py` | Background job definitions |
| 8 | `router.py` | HTTP endpoints |

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap

### Part 13a: Models, Schemas & Email Provider

```
📄 phase4-part13a-notifications-models-schemas-email-provider.md
├── models.py        — NotificationSettings (6 columns, unique user_id, boolean toggles)
├── schemas.py       — SettingsResponse, SettingsUpdate (field_validator for HH:MM), TestEmailRequest
├── email_provider.py — BaseEmailProvider ABC + ConsoleProvider + ResendProvider + SESProvider + factory
└── 005_migration.py  — CREATE TABLE notification_settings

KEY CONCEPTS: Strategy pattern (again!), field_validator for time format, unique per-user row
TIME: ~30 minutes
```

### Part 13b: Service, Tasks & Router

```
📄 phase4-part13b-notifications-service-tasks-router.md
├── service.py  — get/update settings, send_daily_reminder, send_weekly_report,
│                  send_streak_milestone, send_export_ready, _render_template
├── tasks.py    — Celery task definitions: send_daily_reminders, send_weekly_reports,
│                  check_streak_milestones (production: Lambda functions instead)
└── router.py   — 3 endpoints: GET settings, PUT settings, POST test-email

KEY CONCEPTS: Settings CRUD with auto-create, Jinja2 HTML rendering, background tasks
TIME: ~30 minutes
```

### Part 13c: Email Templates & Migration

```
📄 phase4-part13c-notifications-templates-migration.md
├── templates/daily_reminder.html    — "You haven't logged 3 habits today!"
├── templates/weekly_report.html     — "Your weekly report is ready!"
├── templates/streak_milestone.html  — "🔥 30-day streak!"
├── templates/export_ready.html      — "Your export is ready to download"
└── 005_create_notification_settings.py — Migration with unique user_id constraint

KEY CONCEPTS: Jinja2 HTML templates, responsive email design, CTA buttons
TIME: ~20 minutes
```

### Part 13d: Connections & Flows

```
📄 phase4-part13d-notifications-connections-and-flows.md
├── Daily reminder flow (Lambda → query users → check logs → send email)
├── Streak milestone flow (log created → check streak → milestone hit? → email)
├── Cross-module: how AI report triggers notification, how export triggers notification
└── Module summary

TIME: ~15 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   NOTIFICATIONS MODULE                                    │
│                                                                          │
│  TRIGGERS:                                                               │
│  ├── Lambda (daily 8 PM)   → send_daily_reminders task                  │
│  ├── Lambda (Sunday 10 PM) → send_weekly_reports task                   │
│  ├── Lambda (daily 11 PM)  → check_streak_milestones task               │
│  ├── AI Service            → send_weekly_report() after report generated │
│  └── Export Service        → send_export_ready() after file generated   │
│                                                                          │
│  ┌─── router.py (3 endpoints) ──────────────────────────────────────┐   │
│  │  GET  /notifications/settings     → get preferences               │   │
│  │  PUT  /notifications/settings     → update preferences            │   │
│  │  POST /notifications/test-email   → send test email               │   │
│  └──────────────────────────┬────────────────────────────────────────┘   │
│                             │                                            │
│                             ▼                                            │
│  ┌─── service.py ───────────────────────────────────────────────────┐   │
│  │  Settings: get_settings(), update_settings()                      │   │
│  │  Emails:  send_daily_reminder(), send_weekly_report(),            │   │
│  │           send_streak_milestone(), send_export_ready()            │   │
│  │           └── _render_template() → Jinja2 HTML                    │   │
│  └──────────────────────────┬────────────────────────────────────────┘   │
│                             │ uses                                       │
│                             ▼                                            │
│  ┌─── email_provider.py ────────────────────────────────────────────┐   │
│  │  get_email_provider() → Console (dev) / Resend (staging) / SES    │   │
│  │  provider.send(to, subject, html) → True/False                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─── templates/ ───────────────────────────────────────────────────┐   │
│  │  daily_reminder.html | weekly_report.html | streak_milestone.html │   │
│  │  export_ready.html                                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Database: notification_settings (per-user preferences)                  │
│  PostgreSQL: 1 table, unique constraint on user_id                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **Strategy Pattern (3rd time!)** | Same pattern as LLM + email: abstract + implementations + factory | email_provider.py |
| 2 | **Per-user settings** | One row per user with unique constraint, auto-created on first access | models.py |
| 3 | **`field_validator` for time** | Validate `HH:MM` format (00:00 to 23:59) | schemas.py |
| 4 | **HTML email templates** | Jinja2 templates with variables, CTA buttons, responsive design | templates/ |
| 5 | **`_render_template()`** | Load + render Jinja2 HTML file with context variables | service.py |
| 6 | **Resend.com API** | Free email API for staging (100 emails/day) | ResendProvider |
| 7 | **AWS SES with boto3** | Production email via `ses_client.send_email()` | SESProvider |
| 8 | **`run_in_executor()`** | Run synchronous boto3 in async context | SESProvider.send() |
| 9 | **Background tasks** | Celery tasks / Lambda for scheduled email sending | tasks.py |
| 10 | **Idempotent milestones** | Check if milestone was already sent before re-sending | check_streak_milestones |

---

<a name="design-decisions"></a>
## 9. Design Decisions

### Decision 1: Strategy Pattern for Email Providers

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Email Provider Architecture                       │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Strategy pattern — abstract base + 3 providers + factory   │
│                                                                     │
│  WHY (same reasons as LLM providers):                               │
│  • $0 development: console (prints to terminal, no API key)         │
│  • $0 staging: Resend.com (free tier: 100 emails/day)              │
│  • Production: AWS SES (3K/month free from EC2)                     │
│  • Swap via config: EMAIL_PROVIDER=console|resend|ses               │
│                                                                     │
│  WHY NOT JUST SES EVERYWHERE:                                       │
│  • SES requires AWS account + verified domain/email                 │
│  • Console mode lets you see email content in the terminal          │
│  • Resend is simpler for staging (just an API key)                  │
│                                                                     │
│  PATTERN REUSE: This is the THIRD time we use Strategy pattern:     │
│  1. LLM providers (Ollama/Groq/OpenAI)                             │
│  2. Storage providers (Local/S3 — Part 14)                          │
│  3. Email providers (Console/Resend/SES)                            │
│  Same pattern, different domain. Master it once, apply everywhere.  │
│                                                                     │
│  INTERVIEW TIP: "We use the Strategy pattern for email just like    │
│  we do for LLM and storage. Console for dev, Resend for staging,   │
│  SES for production. One env var, zero code changes."               │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Per-User Settings with Auto-Create

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Notification Settings Strategy                    │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Lazy creation — settings row created on first access       │
│                                                                     │
│  WHY NOT CREATE DURING SIGNUP:                                      │
│  • Signup handler stays clean (auth only, no notification logic)    │
│  • Settings are needed LATER (when user visits settings page)       │
│  • Default values (all enabled, 08:00 reminder) are sensible        │
│                                                                     │
│  HOW:                                                               │
│  get_settings(user_id):                                             │
│    → SELECT FROM notification_settings WHERE user_id = ?            │
│    → If not found → CREATE with defaults → return                   │
│                                                                     │
│  unique=True on user_id ensures exactly one row per user.           │
│  Race condition (two simultaneous first-access)? The unique         │
│  constraint catches the duplicate — second request reads the        │
│  existing row.                                                      │
│                                                                     │
│  INTERVIEW TIP: "Settings are lazy-created on first access with     │
│  sensible defaults. This keeps signup clean and avoids creating      │
│  rows for users who never check their notification settings."       │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: How does the notifications module work?
**A:** "Four notification types: daily reminders, streak milestones, weekly report alerts, and export-ready notices. Each is sent via the configured email provider — console for dev, Resend for staging, AWS SES for production. User preferences are stored in a `notification_settings` table with per-toggle control (daily_reminder, weekly_report, streak_alerts) and a configurable reminder time. Scheduled tasks (Lambda or Celery) trigger daily checks: query users with reminders enabled, filter out those who already logged all habits, and send emails to the rest."

### Q2: Why use the Strategy pattern again for email?
**A:** "Same benefits as for LLM providers: development costs $0 (console prints to terminal), staging uses a free email API (Resend, 100/day), and production uses AWS SES. The abstract `BaseEmailProvider` defines `send(to, subject, html) → bool`. Three implementations handle the specifics. The factory reads config. Swapping is one env var. We've now used this pattern three times — LLM, email, and storage. It's the most reusable pattern in the project."

### Q3: How do you handle users who haven't set up notification preferences?
**A:** "Lazy creation with sensible defaults. `get_settings(user_id)` checks if a row exists. If not, it creates one with all notifications enabled and reminder time at 08:00 AM. The `unique=True` constraint on `user_id` ensures one row per user. This avoids cluttering the signup flow with notification logic and means settings only exist for users who need them (or when the scheduled task first checks)."

### Q4: How do daily reminders know which users to notify?
**A:** "The Lambda function (or Celery task) runs at 8 PM UTC. It queries all users with `daily_reminder=True` in `notification_settings`. For each user, it counts logs for today vs active habits. If `logged < total` (user hasn't logged everything), it renders the `daily_reminder.html` template with the user's name, date, and missing habits, then calls `email_provider.send()`. Users who completed all habits get no email — no unnecessary noise."

### Q5: What happens if the email provider is down?
**A:** "`send()` returns `False` (never raises an exception). Email failures are logged as warnings but don't crash the app. The daily reminder task continues to the next user. Failed emails are NOT retried immediately — the next day's scheduled run will send a new reminder. For production, SES has 99.9% uptime. For critical notifications (password reset), we'd add a retry queue, but habit reminders are best-effort."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 12c: AI Migration & Architecture](./phase4-part12c-ai-migration.md) |
| ➡️ Next | [Phase 4 Part 13a: Models, Schemas & Email Provider](./phase4-part13a-notifications-models-schemas-email-provider.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Notifications Sub-Parts

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 13a | [Models, Schemas & Email Provider](./phase4-part13a-notifications-models-schemas-email-provider.md) | models.py + schemas.py + email_provider.py + migration (full source) |
| 13b | [Service, Tasks & Router](./phase4-part13b-notifications-service-tasks-router.md) | service.py + tasks.py + router.py (full source) |
| 13c | [Email Templates & Migration](./phase4-part13c-notifications-templates-migration.md) | 4 HTML templates + 005 migration |
| 13d | [Connections & Flows](./phase4-part13d-notifications-connections-and-flows.md) | Daily reminder flow, streak flow, cross-module triggers |

---

**End of Phase 4 Part 13: Notifications Module Overview**

*Notifications keep users engaged with daily reminders, streak celebrations, and report alerts. The Strategy pattern for email providers is our third application of this design pattern — same concept, different domain. Next: the source code for models, schemas, and the 3-provider email system.*
