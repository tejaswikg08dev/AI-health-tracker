# 🔔 Phase 4 Part 13c: Notifications — Email Templates & Migration

> **"4 HTML email templates using Jinja2 — same template engine as our LLM prompts (Part 08c). Each template has a greeting, content, and CTA button. Responsive design that works on mobile."**

---

## 📋 Document Metadata

| **Previous** | [phase4-part13b-notifications-service-tasks-router.md](./phase4-part13b-notifications-service-tasks-router.md) |
| **Next** | [phase4-part13d-notifications-connections-and-flows.md](./phase4-part13d-notifications-connections-and-flows.md) |
| **Files** | 4 HTML templates + 005 migration (already covered in 13a) |

---

## 1. Template Structure (All 4 Follow This Pattern)

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; }
        h1 { color: #1f2937; }
        .btn { display: inline-block; background: #3B82F6; color: white; padding: 12px 24px;
               text-decoration: none; border-radius: 6px; font-weight: bold; }
        .footer { color: #9ca3af; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- GREETING -->
        <h1>{{ greeting }}</h1>

        <!-- CONTENT (varies per template) -->
        <p>{{ content }}</p>

        <!-- CTA BUTTON -->
        <a href="{{ app_url }}/{{ path }}" class="btn">{{ button_text }}</a>

        <!-- FOOTER -->
        <p class="footer">
            Health Tracker — AI-Powered Personal Health & Habit Tracking<br>
            <a href="{{ app_url }}/settings">Manage notification preferences</a>
        </p>
    </div>
</body>
</html>
```

---

## 2. Template 1: `daily_reminder.html`

```html
<!-- backend/app/modules/notifications/templates/daily_reminder.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white;
                     border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #1f2937; margin-bottom: 10px; }
        .btn { display: inline-block; background: #3B82F6; color: white !important;
               padding: 14px 28px; text-decoration: none; border-radius: 8px;
               font-weight: bold; margin-top: 20px; }
        .footer { color: #9ca3af; font-size: 12px; margin-top: 30px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hi {{ name }}! 👋</h1>
        <p>It's {{ date }} and you haven't logged all your habits yet.</p>
        <p>Taking a minute to log now keeps your streaks alive! 🔥</p>

        <a href="{{ app_url }}/check-in" class="btn">Log Now →</a>

        <p class="footer">
            You're receiving this because you have daily reminders enabled.<br>
            <a href="{{ app_url }}/settings">Turn off reminders</a>
        </p>
    </div>
</body>
</html>
```

## 3. Template 2: `streak_milestone.html`

```html
<!-- backend/app/modules/notifications/templates/streak_milestone.html -->
<!DOCTYPE html>
<html>
<head><!-- same styles --></head>
<body>
    <div class="container">
        <h1>🎉 {{ streak_days }}-Day Streak!</h1>
        <p>Hi {{ name }}!</p>
        <p>INCREDIBLE! You've logged <strong>{{ habit_name }}</strong> for
           <strong>{{ streak_days }} consecutive days</strong>!</p>
        <p>That's real commitment. Keep the momentum going! 💪</p>

        <a href="{{ app_url }}/analytics" class="btn">See Your Streaks →</a>

        <p class="footer">
            <a href="{{ app_url }}/settings">Manage streak alerts</a>
        </p>
    </div>
</body>
</html>
```

## 4. Template 3: `weekly_report.html`

```html
<!-- backend/app/modules/notifications/templates/weekly_report.html -->
<div class="container">
    <h1>📊 Weekly Health Report</h1>
    <p>Hi {{ name }}! Here's your week in review ({{ week_start }} — {{ week_end }}).</p>

    <table style="width:100%; border-collapse:collapse;">
        <tr><td><strong>Habits tracked:</strong></td><td>{{ total_habits }}</td></tr>
        <tr><td><strong>Completion rate:</strong></td><td>{{ completion_pct }}%</td></tr>
        <tr><td><strong>Best streak:</strong></td><td>{{ best_streak }}</td></tr>
    </table>

    <h2>🤖 AI Insights</h2>
    <div style="background:#f0f9ff; padding:15px; border-radius:8px;">
        {{ ai_insights }}
    </div>

    <a href="{{ app_url }}/analytics" class="btn">See Full Report →</a>
</div>
```

## 5. Template 4: `export_ready.html`

```html
<!-- backend/app/modules/notifications/templates/export_ready.html -->
<div class="container">
    <h1>📁 Your Export is Ready!</h1>
    <p>Hi {{ name }}!</p>
    <p>Your {{ file_format | upper }} export ({{ start_date }} to {{ end_date }})
       is ready to download.</p>

    <a href="{{ download_url }}" class="btn">Download {{ file_format | upper }} →</a>

    <p class="footer">This download link expires in 24 hours.</p>
</div>
```

### Jinja2 Features Used in Templates

| Feature | Syntax | Example |
|---------|--------|---------|
| Variable | `{{ name }}` | "Shreya" |
| Filter | `{{ file_format \| upper }}` | "csv" → "CSV" |
| HTML safe | All variables are auto-escaped | Prevents XSS injection |

---

## 6. Migration 005 (Already Shown in Part 13a)

Migration 005 creates the `notification_settings` table with:
- `user_id` UNIQUE FK to users (one row per user)
- 3 boolean toggles (daily_reminder, weekly_report, streak_alerts) defaulting to `true`
- `reminder_time` String(5) defaulting to "08:00"
- Unique index on `user_id`

See Part 13a for the full migration source code.

---

## 7. Navigation

| ⬅️ Previous | [Part 13b: Service, Tasks & Router](./phase4-part13b-notifications-service-tasks-router.md) |
| ➡️ Next | [Part 13d: Connections & Flows](./phase4-part13d-notifications-connections-and-flows.md) |

---

**End of Phase 4 Part 13c: Email Templates & Migration**
