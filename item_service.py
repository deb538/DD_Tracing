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
