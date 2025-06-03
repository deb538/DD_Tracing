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
