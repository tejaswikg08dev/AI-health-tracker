# ============================================================================
# LLM — Prompt Templates
# ============================================================================
# WHAT THIS FILE DOES:
#   Stores all prompt templates used by the AI features.
#   Templates use Jinja2 syntax — variables are injected at runtime.
#
# WHY TEMPLATES (not hardcoded strings):
#   1. Readable — templates are easier to read than f-strings with 20 variables
#   2. Maintainable — change the prompt without touching Python code
#   3. Testable — test templates independently from the LLM call
#   4. Versionable — git diff shows exactly what changed in a prompt
#
# PROMPT ENGINEERING TIPS:
#   - Be specific about the role ("You are a health coach")
#   - Give constraints ("Only reference data provided below")
#   - Include examples of desired output format
#   - Use structured data (tables, lists) for context injection
#   - End with a clear instruction ("Answer the user's question")
# ============================================================================

from jinja2 import Template


# ── System Prompts ──

HEALTH_COACH_SYSTEM = Template("""You are a friendly, knowledgeable personal health coach.
You help users understand their health habits and make better choices.

RULES:
1. Be supportive and encouraging, never judgmental.
2. Reference ACTUAL data from the user's habit logs when available.
3. Use specific numbers: "You averaged 6.8 hours" not "You slept less."
4. If you don't have enough data, say so honestly.
5. Keep responses concise: 3-5 sentences for simple questions, more for analysis.
6. Suggest actionable improvements, not vague advice.
7. If asked about medical conditions, recommend consulting a doctor.

USER INFO:
- Name: {{ user_name }}
- Timezone: {{ timezone }}
- Tracking {{ habit_count }} habits
""")


# ── Context Templates ──

USER_DATA_CONTEXT = Template("""
RECENT HABIT DATA (last {{ days }} days):
{% for date, logs in daily_logs.items() %}
{{ date }}:
{% for log in logs %}  - {{ log.habit_name }}: {{ log.value }} {{ log.unit }}
{% endfor %}{% endfor %}

CURRENT STREAKS:
{% for streak in streaks %}
- {{ streak.habit_name }}: {{ streak.current_streak }} days (best: {{ streak.longest_streak }})
{% endfor %}

WEEKLY COMPARISON (this week vs last week):
{% for habit in weekly %}
- {{ habit.habit_name }}: {{ habit.this_week_avg }} → {{ habit.last_week_avg }}{% if habit.change_pct %} ({{ habit.change_pct }}% change){% endif %}
{% endfor %}
""")


RAG_CONTEXT = Template("""
RELEVANT INFORMATION FROM YOUR DOCUMENTS:
{% for chunk in chunks %}
[Source: {{ chunk.filename }}, Page {{ chunk.page_number }}]
{{ chunk.text }}
---
{% endfor %}

Use the above information to help answer the user's question.
Always cite sources when referencing document content.
""")


# ── Agent Prompts ──

AGENT_SYSTEM = Template("""You are a health coach AI agent with access to tools.

You can use the following tools to gather information before responding:
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
{% endfor %}

INSTRUCTIONS:
1. Think about what information you need to answer the user's question.
2. Use tools to fetch real data — never make up numbers.
3. You can call multiple tools if needed.
4. After gathering data, provide a comprehensive answer.
5. Be specific and reference the actual numbers from the tool results.

USER: {{ user_name }} (tracking {{ habit_count }} habits)
""")


# ── Workflow Prompts ──

WEEKLY_REPORT_ANALYSIS = Template("""Analyze this week's health data and provide insights.

DATA SUMMARY:
{{ data_summary }}

INSTRUCTIONS:
1. Identify the top 3 improvements this week.
2. Identify any concerning trends or declines.
3. Note any correlations you see (e.g., sleep affecting mood).
4. Provide 2-3 specific, actionable recommendations for next week.
5. Keep the tone encouraging and supportive.
6. Reference specific numbers from the data.

Format your response as a structured report with sections:
## Highlights
## Areas to Watch
## Recommendations
""")


WEEKLY_REPORT_WRITER = Template("""Write a personalized weekly health report for {{ user_name }}.

DATA:
{{ data_summary }}

ANALYSIS:
{{ analysis }}

Write a friendly, personalized weekly report. Include:
- A brief greeting mentioning their best achievement
- Key stats in an easy-to-scan format
- The analysis insights in natural language
- A motivating closing message

Keep it under 500 words. Use markdown formatting.
""")


# ── Insight Generation ──

INSIGHT_PROMPT = Template("""Based on this user's health data, generate a brief insight.

DATA:
{{ data_context }}

Generate ONE specific, actionable insight. Examples:
- "Your mood is 23% higher on days you exercise. Try scheduling workouts on your low-mood days."
- "You've been sleeping 45 minutes less on weekdays vs weekends. A consistent sleep schedule could help."

Be specific with numbers. Keep it to 2-3 sentences.
""")
