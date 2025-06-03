
Datadog Integration:
ddtrace.patch() for in-code instrumentation.
Relies on DD_LOGS_INJECTION=true (set via environment variables).
Uses python-json-logger for JSON logging.
Logging:
Configures a shared, application-specific logger in a separate file (logging_config.py).
Uses os.environ for environment variables.
Custom Correlation ID (X-Correlation-ID):
Middleware to extract X-Correlation-ID from incoming headers.
Sets correlation_id as a tag on the Datadog trace span for searchability in Datadog APM.
Demonstrates how to optionally include it in log extra fields.
Modular Code:
main.py for FastAPI app setup and routes.
logging_config.py for centralized logger configuration.
services/item_service.py for business logic demonstrating logger usage across files.
Project Structure



your-fastapi-app/
├── main.py
├── logging_config.py
├── services/
│   └── item_service.py
├── requirements.txt
└── .env  <-- Optional, for local development (if you choose to use python-dotenv)


1. requirements.txt
Create this file in your project root.



fastapi==0.111.0
uvicorn==0.30.1
ddtrace==2.11.0
python-json-logger==2.0.7
python-dotenv==1.0.1  # Only if you plan to use .env file for local setup


2. logging_config.py
This file sets up your structured JSON logger.

Python


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


3. services/item_service.py
This file contains an example service class using the app_logger.

Python


# your-fastapi-app/services/item_service.py

# Import the pre-configured application logger instance
from logging_config import app_logger

class ItemService:
    def __init__(self):
        # We can directly use the imported app_logger instance.
        # If you needed a logger specific to this module's name, you could do:
        # self.logger = logging.getLogger(__name__)
        # but for consistency with the global app_logger, we'll use that.
        self.logger = app_logger

    def process_item_data(self, item_id: int, data: dict):
        """
        Simulates processing item data and logs the steps.
        Logs here will automatically get trace/span IDs if an active span exists.
        """
        self.logger.info(f"ItemService: Starting to process item ID: {item_id}",
                         extra={"item_id": item_id})

        try:
            # Simulate some heavy processing or API calls
            processed_data = {
                "id": item_id,
                "name": data.get("name", f"Item {item_id}"),
                "status": "processed",
                "original_data": data
            }
            self.logger.debug(f"ItemService: Successfully processed data for item ID: {item_id}",
                              extra={"processed_data": processed_data})
            return processed_data
        except Exception as e:
            # Log the error with exception info for detailed stack traces in Datadog
            self.logger.error(f"ItemService: Error processing item ID {item_id}: {e}",
                              exc_info=True,
                              extra={"item_id": item_id})
            raise # Re-raise the exception to be handled by the FastAPI error handler


4. main.py
This is your main FastAPI application file.

Python


# your-fastapi-app/main.py

import os
from fastapi import FastAPI, Request, HTTPException, Response

# --- IMPORTANT: Apply Datadog Patching as early as possible ---
# This activates automatic instrumentation for FastAPI and the logging module.
from ddtrace import patch, tracer
patch(
    logging=True,  # Enables automatic log correlation
    fastapi=True,  # Instruments FastAPI for tracing
    # Add other integrations your app uses, e.g., requests=True, psycopg2=True, redis=True
)

# --- Import the configured logger and services ---
from logging_config import app_logger
from services.item_service import ItemService


# --- Initialize FastAPI App ---
app = FastAPI(
    title=os.getenv("DD_SERVICE", "my-fastapi-app-api"), # Get app title from DD_SERVICE env var
    version=os.getenv("DD_VERSION", "1.0.0"),         # Get app version from DD_VERSION env var
    description="A FastAPI application demonstrating Datadog Tracing and Log Correlation."
)

# Initialize your service instance
item_service = ItemService()


# --- Middleware to handle X-Correlation-ID and general logging context ---
@app.middleware("http")
async def process_request_and_log_context(request: Request, call_next):
    """
    Middleware to:
    1. Extract X-Correlation-ID and attach it as a tag to the Datadog span.
    2. Log request start/end with Datadog trace context.
    """
    correlation_id = request.headers.get("X-Correlation-ID")
    
    # Get the current active span. ddtrace will automatically create one
    # if it's the root of a new trace, or continue an existing one.
    current_span = tracer.current_span

    # Attach the custom correlation_id to the Datadog span if present
    if correlation_id:
        if current_span:
            current_span.set_tag("correlation_id", correlation_id)
            # You can also set it as a resource name if it helps organize traces
            # For example: current_span.resource = f"{request.method} {request.url.path} - {correlation_id}"
            app_logger.debug(f"Attached X-Correlation-ID '{correlation_id}' to current span.")
        else:
            app_logger.warning(f"Received X-Correlation-ID '{correlation_id}' but no active span to attach to. "
                               "This might indicate an issue with ddtrace instrumentation.")

    # Get the log correlation context (contains dd.trace_id, dd.span_id etc.)
    # This is primarily for debugging or if you want to manually include these in specific logs.
    # For standard logging.info/debug/error, they are injected automatically with DD_LOGS_INJECTION=true.
    log_correlation_context = tracer.get_log_correlation_context()

    # Log request start with context (optional, auto-instrumentation covers much of this)
    app_logger.info("Request started", extra={"path": request.url.path, "method": request.method, **log_correlation_context})

    response = await call_next(request)

    # Log request end with context (optional)
    app_logger.info("Request finished", extra={"path": request.url.path, "method": request.method, "status_code": response.status_code, **log_correlation_context})

    return response


# --- FastAPI Routes ---

@app.get("/")
async def read_root():
    """
    Root endpoint that logs a simple message.
    Logs here will automatically get Datadog trace/span IDs.
    """
    app_logger.info("Handling root endpoint request.")
    return {"message": "Hello from FastAPI, traced by Datadog!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, request: Request):
    """
    Endpoint that processes an item using ItemService and logs messages.
    Demonstrates passing correlation_id to logs from the route level.
    """
    # Retrieve X-Correlation-ID from headers for potential use in logs or downstream calls
    correlation_id = request.headers.get("X-Correlation-ID")

    # Prepare extra data for the log message.
    # The correlation_id will be included in the JSON log if it exists.
    log_extra = {"item_id_param": item_id}
    if correlation_id:
        log_extra["request_correlation_id"] = correlation_id # Use a distinct name for clarity

    app_logger.info(f"Received request for item ID: {item_id}", extra=log_extra)

    item_data = {"name": f"Product {item_id}"}

    try:
        # Call into the service layer
        processed_result = item_service.process_item_data(item_id, item_data)
        app_logger.info(f"Successfully processed item {item_id}", extra={"processed_result": processed_result})
        return processed_result
    except Exception as e:
        # FastAPI's HTTPException will automatically return a 500 status.
        # Log the error before re-raising.
        app_logger.error(f"Failed to process item {item_id} in API route: {e}", exc_info=True, extra={"item_id_param": item_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/error")
async def simulate_error():
    """
    Endpoint to simulate an error and see how it's logged and traced.
    """
    app_logger.error("Simulating an intentional error in the /error endpoint.")
    # This will be caught by FastAPI's default error handler and result in a 500.
    # ddtrace will also capture this as an error on the span.
    raise HTTPException(status_code=500, detail="An intentional server error occurred.")



How to Run the Application
Navigate to your project root (your-fastapi-app/).
Create a Python virtual environment (recommended):
Bash
python -m venv venv


Activate the virtual environment:
Linux/macOS: source venv/bin/activate
Windows (Command Prompt): venv\Scripts\activate.bat
Windows (PowerShell): venv\Scripts\Activate.ps1
Install dependencies:
Bash
pip install -r requirements.txt


Set Environment Variables: Linux/macOS (in your active terminal session):
Bash
export DD_SERVICE="my-fastapi-app-service"
export DD_ENV="development"
export DD_VERSION="1.0.0"
export DD_LOGS_INJECTION=true
export LOG_LEVEL="DEBUG" # Set to DEBUG to see all log messages, including debug ones
Windows (Command Prompt):
DOS
set DD_SERVICE=my-fastapi-app-service
set DD_ENV=development
set DD_VERSION=1.0.0
set DD_LOGS_INJECTION=true
set LOG_LEVEL=DEBUG
Windows (PowerShell):
PowerShell
$env:DD_SERVICE="my-fastapi-app-service"
$env:DD_ENV="development"
$env:DD_VERSION="1.0.0"
$env:DD_LOGS_INJECTION="true"
$env:LOG_LEVEL="DEBUG"
If you chose to use python-dotenv and a .env file, you would put these variables in .env and include load_dotenv() at the very top of main.py.
Run your FastAPI application:
Bash
uvicorn main:app --host 0.0.0.0 --port 8000


Testing with curl
1. Basic Request (Datadog generates trace ID):

Bash


curl http://localhost:8000/


You'll see JSON logs with dd.trace_id and dd.span_id generated by Datadog.
2. Request with Custom X-Correlation-ID:

Bash


curl -H "X-Correlation-ID: my-custom-req-12345" http://localhost:8000/items/101


In the logs, you'll see dd.trace_id, dd.span_id, and also your request_correlation_id: "my-custom-req-12345" in the JSON.
In Datadog APM, the trace will have a tag correlation_id:my-custom-req-12345, allowing you to search for it.
This comprehensive setup provides robust tracing and log correlation for your FastAPI application with Datadog.
