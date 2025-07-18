## Datadog Integration:
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

## Project Structure
your-fastapi-app/
├── main.py
├── logging_config.py
├── services/
│   └── item_service.py
├── requirements.txt
└── .env  <-- Optional, for local development (if you choose to use python-dotenv)


## requirements.txt
Create this file in your project root.
fastapi==0.111.0
uvicorn==0.30.1
ddtrace==2.11.0
python-json-logger==2.0.7
python-dotenv==1.0.1  # Only if you plan to use .env file for local setup

### How to Run the Application
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


# Set Environment Variables: 
# Linux/macOS (in your active terminal session):Bash
export DD_SERVICE="my-fastapi-app-service"
export DD_ENV="development"
export DD_VERSION="1.0.0"
export DD_LOGS_INJECTION=true
export LOG_LEVEL="DEBUG" # Set to DEBUG to see all log messages, including debug ones

# Windows (Command Prompt):DOS
set DD_SERVICE=my-fastapi-app-service
set DD_ENV=development
set DD_VERSION=1.0.0
set DD_LOGS_INJECTION=true
set LOG_LEVEL=DEBUG

# EKS
        env:
        - name: DD_SERVICE
          value: "my-fastapi-app"
        - name: DD_ENV
          value: "production"
        - name: DD_VERSION
          value: "1.0.0"
        - name: DD_LOGS_INJECTION
          value: "true" 

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
