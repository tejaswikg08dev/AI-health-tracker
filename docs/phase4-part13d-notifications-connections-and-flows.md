# 🔄 Phase 4 Part 13d: Notifications — Connections & Flows

> **"4 flows: daily reminder (Lambda checks who hasn't logged), streak milestone (check after each log), weekly report alert (after AI generates), export ready (after file generated). Each flow starts with a trigger and ends with an email."**

---

## 📋 Document Metadata

| **Previous** | [phase4-part13c-notifications-templates-migration.md](./phase4-part13c-notifications-templates-migration.md) |
| **Next** | [phase4-part14-export-module-overview.md](./phase4-part14-export-module-overview.md) |

---

## 1. Notifications Module — Complete File Map

```
backend/app/modules/notifications/
├── models.py           ─── Part 13a ── NotificationSettings (6 columns, unique user_id)
├── schemas.py          ─── Part 13a ── SettingsResponse + SettingsUpdate + TestEmailRequest
├── email_provider.py   ─── Part 13a ── BaseEmailProvider + Console + Resend + SES + factory
├── service.py          ─── Part 13b ── get/update settings + 4 send_* email methods
├── tasks.py            ─── Part 13b ── 3 scheduled task definitions
├── router.py           ─── Part 13b ── 3 endpoints (GET/PUT settings, POST test-email)
└── templates/          ─── Part 13c ── 4 HTML email templates (Jinja2)
    ├── daily_reminder.html
    ├── weekly_report.html
    ├── streak_milestone.html
    └── export_ready.html

alembic/versions/005_create_notification_settings.py ─── Part 13a
```

---

## 2. Flow 1: Daily Reminder (Scheduled — 8 PM UTC)

```
TRIGGER: Lambda (CloudWatch Events: cron(0 20 * * ? *)) OR Celery Beat

STEP  COMPONENT                  ACTION                               TIME
────  ─────────                  ──────                               ────
 1    Lambda/Celery              Fires at 8 PM UTC

 2    Task                       Query: SELECT u.*, ns.*
      send_daily_reminders()     FROM users u
                                 JOIN notification_settings ns ON u.id = ns.user_id
                                 WHERE u.is_active = true
                                   AND ns.daily_reminder = true
                                 → 30 users with reminders enabled

 3    For each user:
      │
      ├── Query: SELECT COUNT(DISTINCT habit_id)
      │          FROM habit_logs
      │          WHERE user_id = ? AND log_date = CURRENT_DATE
      │   → logged_today = 3
      │
      ├── Query: SELECT COUNT(*)
      │          FROM habits
      │          WHERE user_id = ? AND is_archived = false
      │   → total_habits = 6
      │
      ├── 3 < 6? → YES, user hasn't logged everything
      │
      ├── NotificationService.send_daily_reminder(
      │     user.email, user.full_name, "2026-09-26"
      │   )
      │   → _render_template("daily_reminder.html", {name, date, app_url})
      │   → email_provider.send(to, subject, html)
      │       ├── Console: prints to terminal
      │       ├── Resend: POST https://api.resend.com/emails
      │       └── SES: boto3 ses_client.send_email()
      │   → True (sent) or False (failed)
      │
      └── Log: {"user": "shreya@test.com", "sent": true}

 4    Task returns:
      {"emails_sent": 22, "skipped": 8 (already logged all), "errors": 0}

TOTAL TIME: ~5-15 seconds (depends on user count + email provider speed)
```

---

## 3. Flow 2: Streak Milestone (Event-Driven)

```
TRIGGER: User logs a habit → POST /logs or POST /logs/bulk

STEP  COMPONENT                  ACTION
────  ─────────                  ──────
 1    LogService.create_log()    New log created for Water Intake, Sep 26

 2    Task triggered:            check_streak_milestones(user_id, habit_id)
      (Lambda via SQS event
       OR Celery task.delay())

 3    Query streak:              AnalyticsRepository.get_streaks(user_id)
                                 → Water Intake: current_streak = 30 days

 4    Is 30 a milestone?         MILESTONES = [7, 14, 21, 30, 60, 90, 100, 180, 365]
                                 30 ∈ MILESTONES → YES!

 5    Check settings:            NotificationSettings.streak_alerts = true? → YES

 6    Check idempotency:         Already sent "30-day Water" milestone?
                                 (check ai_insights or separate tracking)
                                 → No, first time

 7    Send email:                NotificationService.send_streak_milestone(
                                   email, "Shreya", "Water Intake", 30
                                 )
                                 → Template: "🎉 30-Day Streak on Water Intake!"
                                 → email_provider.send()

 8    Log:                       {"milestone_hit": 30, "habit": "Water Intake", "email_sent": true}
```

---

## 4. Flow 3: Weekly Report Alert (After AI Generation)

```
TRIGGER: AI Service generates weekly report (Part 12b)

 1    AiService.generate_weekly_report(user_id, user_name)
        → DataCollector → Analyzer → ReportWriter → AiInsight saved

 2    After successful report generation:
        → NotificationService.send_weekly_report(
            user.email, user.full_name,
            week_start="Sep 20", week_end="Sep 26",
            total_habits=6, completion_pct=78.5,
            best_streak="Water 15 days",
            ai_insights="Your mood correlates with sleep..."
          )

 3    Email sent:
        Subject: "📊 Your Weekly Health Report — Sep 20 to Sep 26"
        Body: summary stats + AI insights + "See Full Report" button
```

---

## 5. Flow 4: Export Ready (After File Generation)

```
TRIGGER: Export Service generates CSV/PDF (Part 14)

 1    ExportService.export_csv(user_id, start, end)
        → CSVGenerator → Storage.save() → download_url

 2    NotificationService.send_export_ready(
        user.email, "Shreya", "CSV",
        start_date="Sep 1", end_date="Sep 30",
        download_url="https://..."
      )

 3    Email sent:
        Subject: "📁 Your Health Tracker Export is Ready"
        Body: "Your CSV export is ready. Download CSV →"
```

---

## 6. Cross-Module Connections

```
┌─── TRIGGERS ────────────────────────────────────────────┐
│                                                          │
│  Lambda/Celery (scheduled)                              │
│    → send_daily_reminders (daily 8 PM)                  │
│    → check_streak_milestones (daily 11 PM)              │
│                                                          │
│  AI Service (Part 12)                                    │
│    → generate_weekly_report() calls send_weekly_report() │
│                                                          │
│  Export Service (Part 14)                                │
│    → export_csv/pdf() calls send_export_ready()          │
│                                                          │
│  Router (user action)                                    │
│    → POST /notifications/test-email                      │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌─── NOTIFICATION SERVICE ─────────────────────────────────┐
│  Check settings → Render template → Email provider → Send │
└──────────────────┬────────────────────────────────────────┘
                   │
                   ▼
┌─── EMAIL PROVIDER (Strategy) ────────────────────────────┐
│  Console (dev) → prints to terminal                       │
│  Resend (staging) → POST api.resend.com                   │
│  SES (production) → boto3 ses_client.send_email()         │
└──────────────────────────────────────────────────────────┘
```

---

## 7. Notifications Module Summary

### What You Built (Parts 13–13d)

| Part | Files | What It Does |
|------|-------|-------------|
| **13** | — | Overview: 4 notification types, email Strategy, architecture |
| **13a** | models, schemas, email_provider, migration | Data layer + 3-provider email system |
| **13b** | service, tasks, router | CRUD + 4 email methods + 3 endpoints |
| **13c** | 4 HTML templates | Jinja2 email templates with CTA buttons |
| **13d** | (this doc) | 4 execution flows, cross-module connections |

### By the Numbers

| Metric | Value |
|--------|-------|
| Python files | 7 |
| HTML templates | 4 |
| Endpoints | 3 (GET settings, PUT settings, POST test-email) |
| Email providers | 3 (Console, Resend, SES) via Strategy pattern |
| Notification types | 4 (daily reminder, streak, weekly report, export) |
| Database table | 1 (notification_settings — unique per user) |
| Scheduled tasks | 3 (daily reminders, weekly reports, streak checks) |

---

## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 13c: Email Templates & Migration](./phase4-part13c-notifications-templates-migration.md) |
| ➡️ Next | [Part 14: Export Module Overview](./phase4-part14-export-module-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Notifications Module — All Sub-Parts Complete ✅

| Sub-Part | Status |
|----------|--------|
| 13a | ✅ Models, Schemas, Email Provider, Migration |
| 13b | ✅ Service, Tasks, Router |
| 13c | ✅ Email Templates |
| **13d** | ✅ **Connections & Flows** |

---

**🎉 The Notifications module is COMPLETE.**

*4 notification types, 3 email providers (Strategy pattern), 4 HTML templates, per-user preferences with opt-out defaults. Users get reminders, celebrations, report alerts, and export notifications — all configurable. Next: the Export module — CSV and PDF generation for data portability.*
