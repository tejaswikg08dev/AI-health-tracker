# ============================================================================
# Health Tracker — Structured Logging Configuration
# ============================================================================
# WHAT THIS FILE DOES:
#   Configures structlog for structured JSON logging.
#
# WHY STRUCTURED LOGGING:
#   Regular logging:  "User 123 created habit 'Water' at 2026-09-26T10:00:00"
#   Structured logging: {"user_id": "123", "action": "create_habit",
#                         "habit_name": "Water", "timestamp": "2026-09-26T10:00:00"}
#
#   Structured logs are:
#   1. Searchable — find all logs where user_id=123 in Elasticsearch
#   2. Parseable — machines can read JSON, not regex on strings
#   3. Dashboardable — Kibana can aggregate by action type, count errors
#
# HOW COMPANIES DO IT:
#   Same. Structured JSON logs → shipped to ELK/Datadog/Splunk → dashboards.
#   This is NOT optional in production — it's how you debug issues at 3 AM.
# ============================================================================

import logging
import sys

import structlog

from app.config import get_settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Call this once at application startup (in main.py lifespan).
    After this, use structlog.get_logger() anywhere in the code.

    Usage:
        logger = structlog.get_logger()
        logger.info("habit_created", user_id=str(user.id), habit_name="Water")

    Output (JSON):
        {"event": "habit_created", "user_id": "abc-123", "habit_name": "Water",
         "timestamp": "2026-09-26T10:00:00Z", "level": "info"}
    """
    settings = get_settings()

    # Determine log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure structlog processors
    # Processors are a pipeline — each one transforms the log event
    shared_processors: list[structlog.types.Processor] = [
        # Add log level (info, warning, error)
        structlog.stdlib.add_log_level,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # If there's an exception, format the traceback
        structlog.processors.format_exc_info,
        # Add caller info (file, line number) — helpful for debugging
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # In development: pretty colored output for readability
    # In production: JSON output for machine parsing (ELK, CloudWatch)
    if settings.APP_ENV == "development":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            # Prepare event dict for standard logging
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard Python logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Route all logs through structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Optional logger name (usually __name__ of the module)

    Usage:
        from app.shared.logging import get_logger
        logger = get_logger(__name__)
        logger.info("something_happened", key="value")
    """
    return structlog.get_logger(name)
