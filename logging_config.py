# your-fastapi-app/logging_config.py

import logging
import os
import sys
from pythonjsonlogger import jsonlogger

def configure_logger():
    """
    Configures the root and application-specific loggers for JSON output.
    Returns the configured application logger instance.
    """
    # Environment variables are accessed directly from os.environ
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOGGER_NAME = os.getenv("DD_SERVICE", "my-fastapi-app") # Use DD_SERVICE as logger name

    # Get the root logger
    root_logger = logging.getLogger()
    # Clear existing handlers to prevent duplicate logs, especially when Uvicorn
    # or other frameworks might set up their own basic handlers.
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    # Set the minimum level for the root logger to capture all messages.
    # This is important so that messages of all levels are passed to handlers.
    root_logger.setLevel(logging.DEBUG)

    # Create a specific logger for your application.
    # This is the logger instance you will import and use throughout your code.
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(LOG_LEVEL)

    # Use a custom JSON formatter.
    # This fmt string includes standard log record attributes.
    # Datadog's log injection (DD_LOGS_INJECTION=true) will automatically add
    # dd.trace_id, dd.span_id, dd.env, dd.service, dd.version as top-level JSON fields.
    formatter = jsonlogger.JsonFormatter(
        fmt='%(levelname)s %(asctime)s %(name)s %(message)s %(lineno)d %(pathname)s'
    )

    # Create a StreamHandler that writes to standard output (where Uvicorn logs to).
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    # Also, ensure logs from ddtrace itself are formatted correctly.
    # This helps in debugging Datadog agent/tracer issues.
    ddtrace_logger = logging.getLogger('ddtrace')
    ddtrace_logger.setLevel(LOG_LEVEL)
    ddtrace_logger.addHandler(log_handler) # Use the same JSON handler

    return logger

# Call configure_logger immediately when this module is imported.
# This ensures the logger is set up once and ready for use.
app_logger = configure_logger()
