# 🏥 AI-Powered Personal Health & Habit Tracker — Complete Project Structure

## Architecture: Modular Monolith + AWS Lambda + React Frontend

---

## Full Directory Tree

```
health-tracker/
│
├── 📁 backend/                              # Python FastAPI Backend (Modular Monolith)
│   ├── 📁 app/                              # Main application package
│   │   ├── __init__.py                      # Package init, version info
│   │   ├── main.py                          # FastAPI app factory, lifespan events, middleware registration
│   │   ├── config.py                        # Pydantic Settings — all env vars, provider configs
│   │   ├── database.py                      # Async SQLAlchemy engine, session factory, connection pool
│   │   ├── redis_client.py                  # Redis async connection manager, connection pool
│   │   ├── dependencies.py                  # Shared dependency injection: get_db, get_current_user, get_redis
│   │   │
│   │   ├── 📁 modules/                      # ══════ MODULAR MONOLITH BOUNDARY ══════
│   │   │   │
│   │   │   ├── 📁 auth/                     # ── MODULE 1: Authentication & Authorization ──
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # POST /signup, /login, /refresh, /logout, GET /me, PUT /me
│   │   │   │   ├── schemas.py               # UserCreate, UserLogin, UserResponse, TokenResponse, UserUpdate
│   │   │   │   ├── service.py               # register_user(), authenticate(), refresh_token(), logout()
│   │   │   │   ├── repository.py            # get_user_by_email(), get_user_by_id(), create_user(), update_user()
│   │   │   │   ├── models.py                # User SQLAlchemy model (id, email, password_hash, full_name, timezone, is_active, created_at)
│   │   │   │   ├── security.py              # hash_password(), verify_password(), create_access_token(), create_refresh_token(), decode_token()
│   │   │   │   └── exceptions.py            # InvalidCredentialsError, UserAlreadyExistsError, TokenExpiredError
│   │   │   │
│   │   │   ├── 📁 habits/                   # ── MODULE 2: Habit Management ──
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # POST /habits, GET /habits, GET /habits/:id, PUT /habits/:id, DELETE /habits/:id, PUT /habits/reorder
│   │   │   │   ├── schemas.py               # HabitCreate, HabitUpdate, HabitResponse, HabitReorderRequest
│   │   │   │   ├── service.py               # create_habit(), update_habit(), delete_habit(), reorder_habits(), validate_habit_limit()
│   │   │   │   ├── repository.py            # CRUD queries, soft delete (archive), reorder with sort_order
│   │   │   │   ├── models.py                # Habit model (id, user_id, name, habit_type[numeric/boolean/scale], unit, target_value, color, icon, sort_order, is_archived, created_at)
│   │   │   │   └── exceptions.py            # HabitNotFoundError, HabitLimitExceededError, DuplicateHabitNameError
│   │   │   │
│   │   │   ├── 📁 logs/                     # ── MODULE 3: Daily Check-ins / Habit Logging ──
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # POST /logs, POST /logs/bulk, GET /logs?date=, GET /logs?start=&end=, PUT /logs/:id, DELETE /logs/:id
│   │   │   │   ├── schemas.py               # LogCreate, BulkLogCreate, LogUpdate, LogResponse, DailyLogSummary
│   │   │   │   ├── service.py               # create_log(), bulk_create_logs(), validate_log_value(), invalidate_analytics_cache()
│   │   │   │   ├── repository.py            # insert log, date range queries, duplicate check (unique: user+habit+date), bulk insert
│   │   │   │   ├── models.py                # HabitLog model (id, user_id, habit_id, log_date, value_numeric, value_boolean, value_scale, notes, created_at, updated_at)
│   │   │   │   └── exceptions.py            # DuplicateLogError, FutureDateError, InvalidValueError
│   │   │   │
│   │   │   ├── 📁 analytics/                # ── MODULE 4: Analytics, Streaks & Insights ──
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # GET /analytics/dashboard, /streaks, /weekly-summary, /monthly-trend, /completion-rate, /correlations
│   │   │   │   ├── schemas.py               # DashboardData, StreakInfo, WeeklySummary, MonthlyTrend, CompletionRate, CorrelationResult, ChartDataPoint
│   │   │   │   ├── service.py               # calculate_streaks(), weekly_comparison(), monthly_trend(), completion_rate(), find_correlations()
│   │   │   │   ├── repository.py            # Complex SQL: window functions for streaks, CTEs for trends, GROUP BY for summaries, LATERAL joins
│   │   │   │   ├── cache.py                 # Redis cache: get_cached(), set_cached(), invalidate_user_cache() — TTL-based caching
│   │   │   │   └── exceptions.py            # InsufficientDataError (not enough logs to analyze)
│   │   │   │
│   │   │   ├── 📁 ai/                       # ── MODULE 5: AI (LLM + RAG + Agents + Agentic Workflows) ──
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # POST /ai/chat (SSE streaming), GET /ai/chat/history, POST /ai/documents, GET /ai/documents, DELETE /ai/documents/:id, POST /ai/insights, GET /ai/weekly-report
│   │   │   │   ├── schemas.py               # ChatRequest, ChatMessage, ChatResponse, DocumentUpload, DocumentResponse, InsightRequest, InsightResponse, WeeklyReportResponse
│   │   │   │   ├── service.py               # Orchestrates: direct chat vs agent chat vs RAG chat, document upload flow, insight generation
│   │   │   │   ├── models.py                # Document model, DocumentChunk model (with vector column), AiChatMessage model, AiInsight model
│   │   │   │   │
│   │   │   │   ├── 📁 llm/                  # ── LLM Integration Layer ──
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base_client.py       # Abstract base class: LLMClient(ABC) — chat(), stream_chat(), embed() methods
│   │   │   │   │   ├── ollama_client.py      # OllamaClient(LLMClient) — calls http://localhost:11434 — FREE, local dev
│   │   │   │   │   ├── groq_client.py        # GroqClient(LLMClient) — calls https://api.groq.com — FREE, cloud deployment
│   │   │   │   │   ├── openai_client.py      # OpenAIClient(LLMClient) — calls https://api.openai.com — PAID, production
│   │   │   │   │   ├── factory.py            # get_llm_client() — returns correct client based on config.LLM_PROVIDER
│   │   │   │   │   ├── prompt_templates.py   # Jinja2 templates: system prompts, user data context, chat, insights, report
│   │   │   │   │   └── token_tracker.py      # Track token usage per user per day — for cost monitoring & rate limiting
│   │   │   │   │
│   │   │   │   ├── 📁 rag/                   # ── RAG (Retrieval-Augmented Generation) Pipeline ──
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── document_processor.py # Extract text from PDF (PyPDF2), TXT, Markdown files
│   │   │   │   │   ├── chunker.py            # Split text into chunks — RecursiveCharacterTextSplitter, configurable chunk_size & overlap
│   │   │   │   │   ├── embeddings.py         # Generate vector embeddings — Ollama (nomic-embed-text) or OpenAI (text-embedding-3-small)
│   │   │   │   │   ├── vector_store.py       # pgvector operations: store_chunks(), similarity_search(), delete_by_document()
│   │   │   │   │   └── retriever.py          # Full retrieval pipeline: embed query → search → rerank → build context with sources
│   │   │   │   │
│   │   │   │   ├── 📁 agents/                # ── AI Agents (ReAct Pattern) ──
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base_agent.py         # Abstract ReAct agent: think → act → observe loop, max_iterations, tool execution
│   │   │   │   │   ├── health_coach.py       # HealthCoachAgent(BaseAgent) — system prompt, tool selection, health-specific logic
│   │   │   │   │   │
│   │   │   │   │   ├── 📁 tools/             # ── Agent Tools (what the agent can call) ──
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── base_tool.py      # Abstract BaseTool: name, description, parameters_schema, execute() — tool interface
│   │   │   │   │   │   ├── query_logs.py     # QueryLogsTool — fetch user's habit data for a date range from DB
│   │   │   │   │   │   ├── get_analytics.py  # GetAnalyticsTool — get streaks, weekly summary, trends from analytics service
│   │   │   │   │   │   ├── search_docs.py    # SearchDocsTool — RAG vector search across user's uploaded documents
│   │   │   │   │   │   ├── correlate.py      # CorrelateTool — calculate Pearson correlation between two habits
│   │   │   │   │   │   └── create_plan.py    # CreatePlanTool — generate a structured habit improvement plan
│   │   │   │   │   │
│   │   │   │   │   └── 📁 memory/            # ── Agent Memory Systems ──
│   │   │   │   │       ├── __init__.py
│   │   │   │   │       ├── short_term.py     # ConversationBuffer — last N messages, sliding window, in-memory per session
│   │   │   │   │       └── long_term.py      # PersistentMemory — key insights saved to DB + Redis, retrieved on new sessions
│   │   │   │   │
│   │   │   │   └── 📁 workflows/             # ── Agentic Workflows (Multi-Step Pipelines) ──
│   │   │   │       ├── __init__.py
│   │   │   │       ├── base_workflow.py      # Abstract BaseWorkflow: define_steps(), execute(), handle_step_failure()
│   │   │   │       ├── orchestrator.py       # WorkflowOrchestrator: runs steps in sequence, retry logic, timeout, logging, fallback
│   │   │   │       └── 📁 weekly_report/     # ── Weekly Report Pipeline (3-Agent Workflow) ──
│   │   │   │           ├── __init__.py
│   │   │   │           ├── data_collector.py # Step 1: DataCollectorAgent — gathers week's habit data, calculates summaries
│   │   │   │           ├── analyzer.py       # Step 2: AnalyzerAgent — finds patterns, uses RAG for health advice, correlations
│   │   │   │           └── report_writer.py  # Step 3: ReportWriterAgent — generates personalized HTML report from data + insights
│   │   │   │
│   │   │   ├── 📁 notifications/             # ── MODULE 6: Notifications & Scheduled Tasks ──
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # GET /notifications/settings, PUT /notifications/settings, POST /notifications/test-email
│   │   │   │   ├── schemas.py               # NotificationSettings, EmailPayload, TestEmailRequest
│   │   │   │   ├── service.py               # send_email(), check_streak_milestones(), format_email_data()
│   │   │   │   ├── models.py                # NotificationSettings model (user_id, daily_reminder, weekly_report, reminder_time, streak_alerts)
│   │   │   │   ├── email_provider.py        # Abstract EmailProvider → ResendProvider, SESProvider, ConsoleProvider (dev: prints to terminal)
│   │   │   │   ├── 📁 templates/            # ── Jinja2 HTML Email Templates ──
│   │   │   │   │   ├── base.html            # Base email layout (header, footer, styles)
│   │   │   │   │   ├── daily_reminder.html  # "Time to log your habits!" with quick-log link
│   │   │   │   │   ├── weekly_report.html   # Weekly summary with charts, AI insights
│   │   │   │   │   ├── streak_milestone.html# "🔥 30-day streak!" celebration email
│   │   │   │   │   └── export_ready.html    # "Your CSV export is ready" with download link
│   │   │   │   └── tasks.py                 # Celery tasks: send_daily_reminders, send_weekly_reports, check_milestones
│   │   │   │
│   │   │   └── 📁 export/                   # ── MODULE 7: Data Export & Reports ──
│   │   │       ├── __init__.py
│   │   │       ├── router.py                # POST /export/csv (async via SQS), GET /export/reports, GET /export/reports/:id/download
│   │   │       ├── schemas.py               # ExportRequest, ExportResponse, ReportMetadata
│   │   │       ├── service.py               # request_csv_export() → SQS, generate_csv_sync() for small exports, list_reports()
│   │   │       ├── csv_generator.py         # Generate CSV from habit logs — streaming rows with io.StringIO
│   │   │       ├── pdf_generator.py         # Generate PDF reports using WeasyPrint or ReportLab
│   │   │       ├── storage.py               # Abstract StorageProvider → MinIOStorage (local), S3Storage (AWS) — same boto3 API
│   │   │       └── exceptions.py            # ExportNotFoundError, StorageError
│   │   │
│   │   ├── 📁 shared/                       # ══════ CROSS-MODULE UTILITIES ══════
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py           # GenericRepository[T]: create(), get(), get_all(), update(), delete() — reusable CRUD
│   │   │   ├── base_schemas.py              # PaginationParams, PaginatedResponse, ErrorResponse, SuccessResponse
│   │   │   ├── date_utils.py                # get_date_range(), to_user_timezone(), start_of_week(), end_of_week()
│   │   │   ├── logging.py                   # Structlog configuration: JSON format, request_id binding, log levels
│   │   │   └── exceptions.py                # BaseAppError, NotFoundError, ConflictError, ValidationError — base exception hierarchy
│   │   │
│   │   └── 📁 middleware/                   # ══════ REQUEST PIPELINE ══════
│   │       ├── __init__.py
│   │       ├── rate_limiter.py              # Redis-based sliding window rate limiter: per IP and per user, configurable limits
│   │       ├── logging_middleware.py        # Log every request: method, path, status, duration, request_id — structlog JSON
│   │       ├── error_handler.py             # Global exception → HTTP response mapping, structured error format
│   │       └── cors.py                      # CORS configuration: allowed origins, methods, headers
│   │
│   ├── 📁 tests/                            # ══════ TEST SUITE ══════
│   │   ├── __init__.py
│   │   ├── conftest.py                      # Master fixtures: test DB (async), test Redis, test client (httpx), auth helpers, cleanup
│   │   ├── factories.py                     # Factory Boy: UserFactory, HabitFactory, HabitLogFactory, DocumentFactory — realistic test data
│   │   │
│   │   ├── 📁 unit/                         # ── Unit Tests (no DB, no Redis, everything mocked) ──
│   │   │   ├── __init__.py
│   │   │   ├── test_auth_security.py        # Test JWT creation/verification, password hashing, token expiry
│   │   │   ├── test_habit_service.py        # Test habit validation, limit checks, reorder logic
│   │   │   ├── test_log_service.py          # Test value validation (numeric range, boolean, scale 1-10), future date rejection
│   │   │   ├── test_analytics_service.py    # Test streak calculation, weekly comparison, completion rate math, correlation
│   │   │   ├── test_ai_context_builder.py   # Test prompt building, data formatting, token counting
│   │   │   ├── test_ai_agent.py             # Test ReAct loop with mocked LLM: tool selection, iteration limit, final answer
│   │   │   ├── test_rag_chunker.py          # Test chunking: size limits, overlap, edge cases (empty doc, single page)
│   │   │   ├── test_rag_retriever.py        # Test retrieval: ranking, source citation building, empty results handling
│   │   │   ├── test_workflow_orchestrator.py# Test step sequencing, retry on failure, fallback, timeout
│   │   │   ├── test_csv_generator.py        # Test CSV output format, headers, date filtering, empty data
│   │   │   ├── test_date_utils.py           # Test timezone conversions, date range edge cases, DST handling
│   │   │   └── test_rate_limiter.py         # Test sliding window logic, per-IP vs per-user limits
│   │   │
│   │   ├── 📁 integration/                  # ── Integration Tests (real DB + Redis via Docker/testcontainers) ──
│   │   │   ├── __init__.py
│   │   │   ├── test_auth_api.py             # Full auth flow: signup → login → refresh → logout → verify token blacklist
│   │   │   ├── test_habits_api.py           # CRUD flow: create → list → update → archive → verify soft delete
│   │   │   ├── test_logs_api.py             # Log flow: create → bulk create → duplicate rejection → date range query
│   │   │   ├── test_analytics_api.py        # Create test data → verify streaks, summaries, trends, cache behavior
│   │   │   ├── test_ai_chat_api.py          # Chat with mocked LLM → verify streaming, history storage, context building
│   │   │   ├── test_ai_documents_api.py     # Upload doc → verify chunks created → search → delete → verify cleanup
│   │   │   ├── test_export_api.py           # Request export → verify SQS message (mocked) or sync CSV content
│   │   │   └── test_notifications_api.py    # Update settings → verify in DB, test email (mocked provider)
│   │   │
│   │   └── 📁 mocks/                       # ── Mock Implementations for Testing ──
│   │       ├── __init__.py
│   │       ├── mock_llm_client.py           # FakeLLMClient: returns predefined responses, simulates tool calls, tracks calls
│   │       ├── mock_email_provider.py       # FakeEmailProvider: stores sent emails in list for assertion
│   │       └── mock_storage.py              # FakeStorage: in-memory file storage, simulates S3/MinIO
│   │
│   ├── 📁 alembic/                          # ══════ DATABASE MIGRATIONS ══════
│   │   ├── env.py                           # Alembic config: async engine, target metadata
│   │   ├── script.py.mako                   # Migration file template
│   │   └── 📁 versions/                     # ── Auto-generated migration files ──
│   │       ├── 001_create_users_table.py
│   │       ├── 002_create_habits_table.py
│   │       ├── 003_create_habit_logs_table.py
│   │       ├── 004_create_streak_cache_table.py
│   │       ├── 005_create_ai_tables.py      # documents, document_chunks (pgvector), ai_chats, ai_insights
│   │       ├── 006_create_notification_settings.py
│   │       ├── 007_create_export_reports_table.py
│   │       └── 008_add_pgvector_extension.py # CREATE EXTENSION vector;
│   │
│   ├── alembic.ini                          # Alembic configuration file
│   ├── requirements.txt                     # Production dependencies
│   ├── requirements-dev.txt                 # Dev + test dependencies (pytest, ruff, mypy, factory-boy)
│   ├── Dockerfile                           # Multi-stage: builder → production (gunicorn + uvicorn workers)
│   ├── Dockerfile.worker                    # Celery worker image (same base, different CMD)
│   ├── .env.example                         # Template: all required environment variables with comments
│   └── pyproject.toml                       # Tool config: ruff (linting), mypy (type checking), pytest settings
│
├── 📁 frontend/                             # ══════ REACT + TYPESCRIPT FRONTEND ══════
│   ├── 📁 src/
│   │   ├── main.tsx                         # App entry point: React root, QueryClientProvider, BrowserRouter
│   │   ├── App.tsx                          # Root component: route definitions, auth guard, layout wrapper
│   │   ├── vite-env.d.ts                    # Vite type declarations
│   │   │
│   │   ├── 📁 types/                        # ── TypeScript Interfaces (mirror backend schemas) ──
│   │   │   ├── user.ts                      # User, AuthTokens, LoginRequest, SignupRequest
│   │   │   ├── habit.ts                     # Habit, HabitType (enum: numeric/boolean/scale), HabitCreate, HabitUpdate
│   │   │   ├── log.ts                       # HabitLog, BulkLogCreate, DailyLogSummary
│   │   │   ├── analytics.ts                # StreakInfo, WeeklySummary, MonthlyTrend, CompletionRate, CorrelationResult, ChartDataPoint
│   │   │   ├── ai.ts                       # ChatMessage, ChatRole (enum: user/assistant/system), DocumentInfo, InsightData
│   │   │   ├── notification.ts             # NotificationSettings
│   │   │   └── common.ts                   # PaginatedResponse<T>, ApiError, SuccessResponse
│   │   │
│   │   ├── 📁 services/                     # ── API Layer (Axios HTTP calls) ──
│   │   │   ├── api.ts                       # Axios instance: base URL, auth interceptor (attach JWT), refresh interceptor (auto-refresh expired token), error interceptor
│   │   │   ├── auth.service.ts              # login(), signup(), refreshToken(), logout(), getProfile(), updateProfile()
│   │   │   ├── habit.service.ts             # getHabits(), createHabit(), updateHabit(), deleteHabit(), reorderHabits()
│   │   │   ├── log.service.ts               # createLog(), bulkCreateLogs(), getLogs(), getLogsByDateRange(), updateLog(), deleteLog()
│   │   │   ├── analytics.service.ts         # getDashboard(), getStreaks(), getWeeklySummary(), getMonthlyTrend(), getCompletionRate(), getCorrelations()
│   │   │   ├── ai.service.ts               # streamChat() (SSE EventSource), getChatHistory(), uploadDocument(), getDocuments(), deleteDocument(), getInsights(), getWeeklyReport()
│   │   │   ├── notification.service.ts     # getSettings(), updateSettings(), sendTestEmail()
│   │   │   └── export.service.ts           # requestCsvExport(), getReports(), downloadReport()
│   │   │
│   │   ├── 📁 hooks/                        # ── Custom React Hooks (TanStack Query wrappers) ──
│   │   │   ├── useAuth.ts                   # useLogin(), useSignup(), useLogout(), useProfile() — mutation + query hooks
│   │   │   ├── useHabits.ts                 # useHabits() query, useCreateHabit() mutation, useUpdateHabit(), useDeleteHabit()
│   │   │   ├── useLogs.ts                   # useTodayLogs(), useLogsByRange(), useCreateLog(), useBulkLog()
│   │   │   ├── useAnalytics.ts              # useDashboard(), useStreaks(), useWeeklySummary(), useMonthlyTrend(), useCorrelations()
│   │   │   ├── useChat.ts                   # useChat() — manages messages state, streaming SSE, send/receive, history
│   │   │   ├── useDocuments.ts              # useDocuments(), useUploadDocument(), useDeleteDocument()
│   │   │   └── useNotifications.ts          # useNotificationSettings(), useUpdateSettings()
│   │   │
│   │   ├── 📁 store/                        # ── Global State (Zustand) ──
│   │   │   └── auth-store.ts                # user, tokens, isAuthenticated, login(), logout(), setTokens() — persisted to localStorage
│   │   │
│   │   ├── 📁 components/                   # ── Reusable UI Components ──
│   │   │   │
│   │   │   ├── 📁 layout/                   # ── Page Layout Components ──
│   │   │   │   ├── Navbar.tsx               # Top navigation: logo, user menu, theme toggle
│   │   │   │   ├── Sidebar.tsx              # Side navigation: Dashboard, Habits, Check-in, Analytics, AI Chat, Settings links
│   │   │   │   ├── PageLayout.tsx           # Layout wrapper: Navbar + Sidebar + main content area
│   │   │   │   ├── ProtectedRoute.tsx       # Auth guard: redirect to /login if not authenticated
│   │   │   │   └── LoadingSpinner.tsx       # Full-page and inline loading indicators
│   │   │   │
│   │   │   ├── 📁 habits/                   # ── Habit Management Components ──
│   │   │   │   ├── HabitCard.tsx            # Single habit card: name, icon, color, streak badge, target, edit/delete actions
│   │   │   │   ├── HabitForm.tsx            # Create/Edit form: name, type selector, unit, target, color picker, icon picker
│   │   │   │   ├── HabitList.tsx            # Grid/list of HabitCards with empty state
│   │   │   │   ├── HabitTypeSelector.tsx    # Radio group: Numeric (e.g., 8 glasses), Boolean (yes/no), Scale (1-10)
│   │   │   │   └── StreakBadge.tsx          # 🔥 streak display: current streak count, fire animation at milestones
│   │   │   │
│   │   │   ├── 📁 logs/                     # ── Daily Logging Components ──
│   │   │   │   ├── DailyCheckIn.tsx         # Today's check-in form: lists all active habits with input for each
│   │   │   │   ├── HabitLogInput.tsx        # Single habit input — adapts by type: number input, toggle switch, slider (1-10)
│   │   │   │   ├── LogHistory.tsx           # Table/timeline of past log entries with date picker
│   │   │   │   ├── DateNavigator.tsx        # Previous/Next day navigation with calendar popup
│   │   │   │   └── QuickLogButton.tsx       # One-tap logging for boolean habits (did it / didn't)
│   │   │   │
│   │   │   ├── 📁 charts/                   # ── Data Visualization Components (Recharts) ──
│   │   │   │   ├── WeeklyBarChart.tsx       # Bar chart: daily values for selected habit this week
│   │   │   │   ├── MonthlyLineChart.tsx     # Line chart: 30-day trend with moving average line
│   │   │   │   ├── CompletionPieChart.tsx   # Pie/donut chart: completion percentage per habit
│   │   │   │   ├── StreakCalendar.tsx       # GitHub-style contribution calendar: color-coded by completion
│   │   │   │   ├── ComparisonBarChart.tsx   # Side-by-side bars: this week vs last week per habit
│   │   │   │   └── CorrelationChart.tsx     # Scatter plot: habit A vs habit B with trend line
│   │   │   │
│   │   │   ├── 📁 ai/                       # ── AI Chat & Document Components ──
│   │   │   │   ├── ChatWindow.tsx           # Full chat interface: message list, scroll, loading indicator
│   │   │   │   ├── ChatMessage.tsx          # Single message bubble: user (right) or AI (left), markdown rendering, sources
│   │   │   │   ├── ChatInput.tsx            # Message input: text area, send button, keyboard shortcut (Enter)
│   │   │   │   ├── StreamingText.tsx        # Animated text that appears word-by-word (for SSE streaming)
│   │   │   │   ├── DocumentUpload.tsx       # Drag-and-drop file upload: PDF/TXT, progress bar, file list
│   │   │   │   ├── DocumentList.tsx         # List of uploaded documents: name, status (processing/ready), delete
│   │   │   │   ├── SourceCitation.tsx       # Clickable source reference: [Source: filename.pdf, p.3]
│   │   │   │   └── InsightCard.tsx          # AI-generated insight card: icon, title, description, action suggestion
│   │   │   │
│   │   │   ├── 📁 dashboard/                # ── Dashboard Widgets ──
│   │   │   │   ├── SummaryCards.tsx          # Top row cards: total habits, today's progress, longest streak, completion rate
│   │   │   │   ├── TodayProgress.tsx        # Circular progress: X of Y habits logged today
│   │   │   │   ├── TopStreaks.tsx            # Top 3 active streaks with fire emoji and count
│   │   │   │   ├── WeeklyOverview.tsx       # Mini bar chart: this week's daily completion count
│   │   │   │   └── AiInsightWidget.tsx      # Latest AI insight/tip from weekly report
│   │   │   │
│   │   │   └── 📁 ui/                       # ── Shadcn/ui Base Components (generated via CLI) ──
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── input.tsx
│   │   │       ├── label.tsx
│   │   │       ├── select.tsx
│   │   │       ├── dialog.tsx               # Modal dialogs (create habit, confirm delete)
│   │   │       ├── toast.tsx                # Toast notifications (success, error)
│   │   │       ├── dropdown-menu.tsx
│   │   │       ├── tabs.tsx
│   │   │       ├── badge.tsx
│   │   │       ├── slider.tsx               # For scale (1-10) habit input
│   │   │       ├── switch.tsx               # For boolean habit input
│   │   │       ├── calendar.tsx             # Date picker calendar
│   │   │       ├── popover.tsx
│   │   │       ├── avatar.tsx
│   │   │       ├── separator.tsx
│   │   │       ├── skeleton.tsx             # Loading skeleton placeholders
│   │   │       ├── progress.tsx             # Progress bar
│   │   │       ├── scroll-area.tsx
│   │   │       └── tooltip.tsx
│   │   │
│   │   ├── 📁 pages/                        # ── Page Components (one per route) ──
│   │   │   ├── LoginPage.tsx                # Email + password form, link to signup, error messages
│   │   │   ├── SignupPage.tsx               # Full name + email + password + timezone form, link to login
│   │   │   ├── DashboardPage.tsx            # Main dashboard: SummaryCards + TodayProgress + TopStreaks + WeeklyOverview + AiInsight
│   │   │   ├── HabitsPage.tsx               # Habit management: HabitList + "Add Habit" button + HabitForm dialog
│   │   │   ├── CheckInPage.tsx              # Daily check-in: DateNavigator + DailyCheckIn form + "Save All" button
│   │   │   ├── AnalyticsPage.tsx            # Analytics dashboard: tabs for Streaks, Weekly, Monthly, Correlations + charts
│   │   │   ├── ChatPage.tsx                 # AI chat: ChatWindow + DocumentUpload sidebar + DocumentList
│   │   │   ├── ReportsPage.tsx              # Weekly reports list: date, download PDF, view online
│   │   │   └── SettingsPage.tsx             # Profile edit, notification preferences, timezone, export CSV, danger zone (delete account)
│   │   │
│   │   └── 📁 lib/                          # ── Utility Functions ──
│   │       ├── utils.ts                     # cn() class name helper (tailwind-merge), formatNumber(), truncateText()
│   │       ├── date-helpers.ts              # formatDate(), getRelativeTime(), getWeekRange(), getMonthRange()
│   │       └── constants.ts                 # HABIT_COLORS, HABIT_ICONS, DEFAULT_HABITS, STREAK_MILESTONES
│   │
│   ├── 📁 public/                           # Static assets
│   │   ├── favicon.ico
│   │   ├── logo.svg
│   │   └── manifest.json
│   │
│   ├── index.html                           # HTML entry point
│   ├── package.json                         # Dependencies, scripts: dev, build, lint, test, preview
│   ├── package-lock.json
│   ├── tsconfig.json                        # TypeScript config: strict mode, path aliases
│   ├── tsconfig.node.json                   # TypeScript config for Vite/Node
│   ├── tailwind.config.js                   # Tailwind: custom colors, fonts, animations
│   ├── postcss.config.js                    # PostCSS: tailwind + autoprefixer
│   ├── vite.config.ts                       # Vite: proxy /api to backend, port, HMR
│   ├── eslint.config.js                     # ESLint: TypeScript + React rules
│   ├── components.json                      # Shadcn/ui configuration
│   ├── Dockerfile                           # Multi-stage: install → build → nginx serve
│   └── .env.example                         # VITE_API_URL, VITE_APP_NAME
│
├── 📁 lambda_functions/                     # ══════ AWS LAMBDA FUNCTIONS (Event-Driven) ══════
│   │
│   ├── 📁 01_daily_reminder/                # ── Lambda 1: Daily Habit Reminder ──
│   │   ├── handler.py                       # Trigger: EventBridge cron (8 AM daily)
│   │   │                                    # Flow: Query users with reminders ON + not logged today → Send email via SES
│   │   └── requirements.txt                 # boto3, psycopg2-binary
│   │
│   ├── 📁 02_weekly_report_generator/       # ── Lambda 2: Weekly AI Report ──
│   │   ├── handler.py                       # Trigger: EventBridge cron (Sunday 9 AM)
│   │   │                                    # Flow: Gather week data → Call Groq LLM for insights → Generate HTML → Save PDF to S3 → Email via SES
│   │   └── requirements.txt                 # boto3, psycopg2-binary, httpx, jinja2, weasyprint
│   │
│   ├── 📁 03_csv_export/                    # ── Lambda 3: Async CSV Export ──
│   │   ├── handler.py                       # Trigger: SQS message (from FastAPI POST /export/csv)
│   │   │                                    # Flow: Query logs → Generate CSV → Upload to S3 → Send download link email
│   │   └── requirements.txt                 # boto3, psycopg2-binary
│   │
│   ├── 📁 04_streak_milestone/              # ── Lambda 4: Streak Milestone Checker ──
│   │   ├── handler.py                       # Trigger: SQS message (from FastAPI on new log creation)
│   │   │                                    # Flow: Calculate streak → Check milestones (7,30,100 days) → Send congrats email
│   │   └── requirements.txt                 # boto3, psycopg2-binary
│   │
│   ├── 📁 05_data_cleanup/                  # ── Lambda 5: Monthly Data Cleanup ──
│   │   ├── handler.py                       # Trigger: EventBridge cron (1st of month)
│   │   │                                    # Flow: Delete expired tokens, old chats (90d), orphaned S3 files, VACUUM ANALYZE
│   │   └── requirements.txt                 # boto3, psycopg2-binary
│   │
│   ├── 📁 06_document_processor/            # ── Lambda 6: RAG Document Processor ──
│   │   ├── handler.py                       # Trigger: S3 PutObject event (user uploads PDF)
│   │   │                                    # Flow: Download from S3 → Extract text → Chunk → Generate embeddings → Store in pgvector
│   │   └── requirements.txt                 # boto3, psycopg2-binary, PyPDF2, httpx, tiktoken
│   │
│   ├── 📁 shared/                           # ── Shared Utilities Across Lambdas ──
│   │   ├── __init__.py
│   │   ├── db_utils.py                      # get_db_connection(): PostgreSQL connection with connection pooling, env-based config
│   │   ├── email_utils.py                   # send_email(): SES wrapper with HTML template rendering
│   │   ├── s3_utils.py                      # upload_file(), download_file(), generate_presigned_url(), delete_file()
│   │   └── config.py                        # Lambda environment config: DB_URL, S3_BUCKET, SES_FROM_EMAIL, GROQ_API_KEY
│   │
│   ├── 📁 tests/                            # ── Lambda Tests ──
│   │   ├── conftest.py                      # Lambda test fixtures, mock AWS services (moto)
│   │   ├── test_daily_reminder.py           # Test user query, email sending, error handling
│   │   ├── test_weekly_report.py            # Test data gathering, LLM call (mocked), PDF generation, S3 upload
│   │   ├── test_csv_export.py               # Test SQS message parsing, CSV generation, S3 upload, presigned URL
│   │   ├── test_streak_milestone.py         # Test streak calculation, milestone detection, idempotency check
│   │   ├── test_data_cleanup.py             # Test cleanup queries, S3 file deletion
│   │   └── test_document_processor.py       # Test PDF extraction, chunking, embedding call (mocked), pgvector insert
│   │
│   ├── template.yaml                        # AWS SAM template: all Lambda functions, SQS queues, S3 buckets, EventBridge rules, IAM roles
│   ├── samconfig.toml                       # SAM deployment configuration: stack name, region, capabilities
│   └── events/                              # ── Sample Event Payloads for Local Testing ──
│       ├── daily_reminder_event.json        # EventBridge scheduled event
│       ├── sqs_export_event.json            # SQS message with export request
│       ├── sqs_streak_event.json            # SQS message with new log event
│       ├── s3_upload_event.json             # S3 PutObject event with document info
│       └── weekly_report_event.json         # EventBridge scheduled event
│
├── 📁 nginx/                                # ══════ NGINX REVERSE PROXY ══════
│   ├── nginx.conf                           # Main config: worker_processes, events block, http block
│   ├── default.conf                         # Server block: proxy_pass to backend, static files, rate limiting, WebSocket, SSE, security headers, gzip
│   └── ssl/                                 # SSL certificates (self-signed for local, Let's Encrypt for deploy)
│       └── .gitkeep
│
├── 📁 .github/                              # ══════ CI/CD ══════
│   ├── 📁 workflows/
│   │   ├── ci.yml                           # Main pipeline: lint (ruff, mypy, eslint) → test (pytest, vitest) → build (Docker, React) → deploy
│   │   ├── backend-tests.yml                # Backend-only: runs on backend/** changes — pytest with PostgreSQL + Redis services
│   │   ├── frontend-tests.yml               # Frontend-only: runs on frontend/** changes — vitest + build check
│   │   └── lambda-tests.yml                 # Lambda-only: runs on lambda_functions/** changes — pytest with moto (AWS mocks)
│   └── 📁 ISSUE_TEMPLATE/
│       ├── bug_report.md                    # Bug report template
│       └── feature_request.md               # Feature request template
│
├── 📁 docs/                                 # ══════ DOCUMENTATION (Interview Prep) ══════
│   ├── 📁 architecture/
│   │   ├── HLD.md                           # High-Level Design: system diagram, component overview, data flow, tech choices with rationale
│   │   ├── LLD.md                           # Low-Level Design: class diagrams, sequence diagrams, algorithm details (streak calc, rate limiter)
│   │   ├── database-design.md               # ER diagram, table schemas, index strategy, query patterns
│   │   ├── api-design.md                    # REST API conventions, endpoint summary, auth flow, error format
│   │   └── ai-architecture.md              # LLM integration, RAG pipeline, agent design, workflow orchestration
│   ├── 📁 deployment/
│   │   ├── local-setup.md                   # Step-by-step: clone → docker-compose up → seed data → access app
│   │   ├── staging-deploy.md                # Deploy to Render + Vercel + Supabase (free tier guide)
│   │   ├── aws-deploy.md                    # Production AWS architecture (documented, not deployed — costs money)
│   │   └── lambda-deploy.md                 # SAM deploy guide: sam build → sam deploy
│   ├── 📁 learning-notes/                   # ── Your Personal Learning Journal ──
│   │   ├── week-1-notes.md                  # What you learned each week
│   │   ├── week-2-notes.md
│   │   ├── week-3-notes.md
│   │   ├── week-4-notes.md
│   │   └── week-5-notes.md
│   └── 📁 interview-prep/
│       ├── system-design-answers.md         # Prepared answers: "Design a habit tracker", "Design a notification system"
│       ├── ai-concepts.md                   # RAG explained, Agents explained, Agentic workflows explained — in your own words
│       └── sql-queries.md                   # All complex queries from this project with explanations
│
├── 📁 scripts/                              # ══════ UTILITY SCRIPTS ══════
│   ├── seed_data.py                         # Populate DB with sample data: demo user, habits, 30 days of logs
│   ├── generate_fake_data.py                # Generate realistic habit logs for testing charts/analytics
│   ├── setup_ollama.sh                      # Pull required Ollama models: llama3.1:8b, nomic-embed-text
│   └── reset_db.sh                          # Drop all tables, re-run migrations, re-seed (dev only)
│
├── docker-compose.yml                       # ══════ PRODUCTION-LIKE COMPOSE ══════
│                                            # Services: nginx, backend (x2 replicas), celery-worker, celery-beat,
│                                            # postgres (pgvector), redis, ollama, minio
│                                            # All with health checks, resource limits, restart policies
│
├── docker-compose.dev.yml                   # ══════ DEVELOPMENT COMPOSE (OVERRIDE) ══════
│                                            # Adds: volume mounts for hot reload, debug ports,
│                                            # single backend replica, Elasticsearch + Kibana (optional)
│                                            # Usage: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
│
├── docker-compose.test.yml                  # ══════ TEST COMPOSE ══════
│                                            # Minimal: postgres + redis only — for running pytest locally
│
├── Makefile                                 # ══════ SHORTCUT COMMANDS ══════
│                                            # make dev        → start dev environment
│                                            # make test       → run all tests
│                                            # make test-unit  → run unit tests only
│                                            # make test-int   → run integration tests only
│                                            # make lint       → run ruff + mypy + eslint
│                                            # make migrate    → run alembic migrations
│                                            # make seed       → seed sample data
│                                            # make build      → build Docker images
│                                            # make clean      → remove containers, volumes
│                                            # make logs       → tail all container logs
│
├── .env.example                             # ══════ ENVIRONMENT VARIABLES TEMPLATE ══════
│                                            # DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/healthtracker
│                                            # REDIS_URL=redis://localhost:6379/0
│                                            # SECRET_KEY=your-secret-key-change-this
│                                            # LLM_PROVIDER=ollama  (ollama | groq | openai)
│                                            # LLM_MODEL=llama3.1:8b
│                                            # OLLAMA_BASE_URL=http://localhost:11434
│                                            # GROQ_API_KEY=your-groq-key (free)
│                                            # S3_ENDPOINT=http://localhost:9000 (MinIO)
│                                            # S3_BUCKET=health-tracker
│                                            # S3_ACCESS_KEY=minioadmin
│                                            # S3_SECRET_KEY=minioadmin
│                                            # EMAIL_PROVIDER=console (console | resend | ses)
│                                            # RESEND_API_KEY=your-resend-key (free)
│                                            # CORS_ORIGINS=http://localhost:3000
│
├── .gitignore                               # Python, Node, Docker, env files, IDE files, coverage, OS files
├── .dockerignore                            # node_modules, __pycache__, .git, .env, tests, docs
├── .pre-commit-config.yaml                  # Pre-commit hooks: ruff, mypy, eslint, prettier — run before every commit
│
└── README.md                                # ══════ PROJECT README ══════
                                             # Project overview, architecture diagram, tech stack, quick start guide,
                                             # screenshots, API docs link, folder structure summary, contributing guide
```

---

## File Count Summary

| Area | Files | Lines of Code (Estimated) |
|------|-------|---------------------------|
| Backend — Modules (7 modules) | ~55 files | ~4,000 - 5,500 |
| Backend — AI (LLM + RAG + Agents + Workflows) | ~25 files | ~2,000 - 2,500 |
| Backend — Shared + Middleware | ~10 files | ~400 - 600 |
| Backend — Tests | ~25 files | ~2,500 - 3,000 |
| Backend — Migrations | ~8 files | ~300 - 400 |
| Frontend — Pages | ~9 files | ~1,500 - 2,000 |
| Frontend — Components | ~35 files | ~3,000 - 4,000 |
| Frontend — Services + Hooks + Store | ~18 files | ~1,200 - 1,500 |
| Frontend — Types + Utils | ~10 files | ~400 - 500 |
| Lambda Functions | ~12 files | ~800 - 1,000 |
| Lambda Tests | ~7 files | ~500 - 700 |
| Config (Docker, Nginx, CI/CD, etc.) | ~20 files | ~800 - 1,000 |
| Documentation | ~12 files | ~1,500 - 2,000 |
| Scripts | ~4 files | ~200 - 300 |
| **TOTAL** | **~250 files** | **~19,100 - 25,000 lines** |

---

## Module Dependency Map

```
                        ┌──────────┐
                        │   Auth   │  ← Foundation (no dependencies)
                        └────┬─────┘
                             │ user identity
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼───┐    ┌────▼────┐   ┌─────▼──────────┐
         │ Habits │    │  Logs   │   │ Notifications  │
         └────┬───┘    └────┬────┘   └────────┬───────┘
              │             │                  │
              └──────┬──────┘                  │
                     │ habit data + logs       │
              ┌──────▼──────┐                  │
              │  Analytics  │                  │
              └──────┬──────┘                  │
                     │ analytics data          │
              ┌──────▼──────┐                  │
              │     AI      │──────────────────┘
              │ LLM+RAG+    │ triggers notifications
              │ Agent+Flow  │
              └──────┬──────┘
                     │ report data
              ┌──────▼──────┐
              │   Export    │
              └─────────────┘

  Lambda Functions connect to:
  ├── PostgreSQL (same DB as FastAPI)
  ├── S3 / MinIO (file storage)
  ├── SES (email sending)
  └── SQS (receives events from FastAPI)
```

---

## Build Order (Week by Week)

```
Week 1: Auth → Habits → Logs → Analytics → Redis Cache
        (Backend modules 1-4, all connected)

Week 2: Frontend: Login → Dashboard → Habits → CheckIn → Analytics → Charts
        (React pages and components)

Week 3: AI Module: LLM Client → RAG Pipeline → Chat UI
        (Ollama setup, document upload, vector search, streaming chat)

Week 4: AI Agents → Agentic Workflow → Lambda Functions
        (ReAct agent, tools, memory, weekly report pipeline, all 6 Lambdas)

Week 5: Nginx → Docker Prod → CI/CD → Testing → Deploy → Documentation
        (Infrastructure, deploy to free tier, write HLD/LLD)
```
