"""Load Balancer handler for executing remote functions via HTTP.

This handler provides a FastAPI application for the Load Balancer runtime.
It supports:
- /ping: Health check endpoint (required by RunPod Load Balancer)
- /execute: Remote function execution via HTTP POST (QB endpoint mode)
- User's FastAPI app routes (LB endpoint mode)

The handler uses worker-flash's RemoteExecutor for function execution.

LB Endpoint Mode (FLASH_ENDPOINT_TYPE=lb):
- Imports user's FastAPI application from FLASH_MAIN_FILE
- Loads the app object from FLASH_APP_VARIABLE
- Preserves all user routes and middleware
- Adds /ping health check endpoint

QB Endpoint Mode (FLASH_ENDPOINT_TYPE not set or not "lb"):
- Creates generic FastAPI app with /execute endpoint
- Uses RemoteExecutor for function execution
"""

import importlib.util
import logging
import os
from typing import Any, Dict

from fastapi import FastAPI

from logger import setup_logging
from unpack_volume import maybe_unpack

# Initialize logging configuration
setup_logging()
logger = logging.getLogger(__name__)

# Unpack Flash deployment artifacts if running in Flash mode
# This is a no-op for Live Serverless and local development
maybe_unpack()

# Import from bundled /app/runpod_flash (no system package)
# These imports must happen AFTER maybe_unpack() so /app is in sys.path
from runpod_flash.protos.remote_execution import FunctionRequest, FunctionResponse  # noqa: E402
from remote_executor import RemoteExecutor  # noqa: E402


def _is_lb_endpoint() -> bool:
    """Determine if this endpoint runs in LB mode (serves user FastAPI routes)."""
    if os.getenv("FLASH_ENDPOINT_TYPE") == "lb":
        return True
    if os.getenv("FLASH_IS_MOTHERSHIP") == "true":
        logger.warning("FLASH_IS_MOTHERSHIP is deprecated. Use FLASH_ENDPOINT_TYPE=lb instead.")
        return True
    return False


is_lb_endpoint = _is_lb_endpoint()

if is_lb_endpoint:
    # LB endpoint mode: Import user's FastAPI application
    try:
        main_file = os.getenv("FLASH_MAIN_FILE", "main.py")
        app_variable = os.getenv("FLASH_APP_VARIABLE", "app")

        logger.info(f"LB endpoint mode: Importing {app_variable} from {main_file}")

        # Dynamic import of user's module
        spec = importlib.util.spec_from_file_location("user_main", main_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot find or load {main_file}")

        user_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_module)

        # Get the FastAPI app from user's module
        if not hasattr(user_module, app_variable):
            raise AttributeError(f"Module {main_file} does not have '{app_variable}' attribute")

        app = getattr(user_module, app_variable)

        if not isinstance(app, FastAPI):
            raise TypeError(
                f"Expected FastAPI instance, got {type(app).__name__} for {app_variable}"
            )

        logger.info(f"Successfully imported FastAPI app '{app_variable}' from {main_file}")

        # Add /ping endpoint if not already present
        # Check if /ping route already exists to avoid adding a duplicate health check endpoint
        ping_exists = any(getattr(route, "path", None) == "/ping" for route in app.routes)

        if not ping_exists:

            @app.get("/ping")
            async def ping_lb() -> Dict[str, Any]:
                """Health check endpoint for LB (added by framework)."""
                return {
                    "status": "healthy",
                    "endpoint": "lb",
                    "id": os.getenv("RUNPOD_ENDPOINT_ID", "unknown"),
                }

            logger.info("Added /ping endpoint to user's FastAPI app")

    except Exception as error:
        logger.error(f"Failed to initialize LB endpoint mode: {error}", exc_info=True)
        raise

else:
    # Queue-based mode: Create generic Load Balancer handler app
    app = FastAPI(title="Load Balancer Handler")
    logger.info("QB endpoint mode: Using generic Load Balancer handler")


# Queue-based mode endpoints
if not is_lb_endpoint:

    @app.get("/ping")
    async def ping() -> Dict[str, Any]:
        """Ping endpoint for health checks (RunPod Load Balancer requirement).

        Returns HTTP 200 when healthy. RunPod measures cold start by tracking
        the transition from 204 (initializing) to 200 (healthy).
        """
        return {"status": "healthy"}

    @app.post("/execute")
    async def execute(request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a remote function via HTTP POST request.

        Expects FunctionRequest JSON payload.
        Supports both direct FunctionRequest format and RunPod wrapped format.
        """
        output: FunctionResponse

        try:
            executor = RemoteExecutor()
            # Handle both direct FunctionRequest and RunPod wrapped format
            request_data = request.get("input", request)
            input_data = FunctionRequest(**request_data)
            output = await executor.ExecuteFunction(input_data)

        except Exception as error:
            output = FunctionResponse(
                success=False,
                error=f"Error in handler: {str(error)}",
            )

        return output.model_dump()  # type: ignore[no-any-return]


if __name__ == "__main__":
    import uvicorn

    # Local development server for testing
    uvicorn.run(app, host="0.0.0.0", port=80)
