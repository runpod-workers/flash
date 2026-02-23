"""Load Balancer handler for executing remote functions via HTTP.

This handler provides a FastAPI application for the Load Balancer runtime.
It supports:
- /ping: Health check endpoint (required by RunPod Load Balancer)
- /execute: Remote function execution via HTTP POST (QB endpoint mode)
- User's FastAPI app routes (LB endpoint mode)

The handler uses worker-flash's RemoteExecutor for function execution.

LB Endpoint Mode (FLASH_ENDPOINT_TYPE=lb):
- Auto-discovers generated handler from FLASH_RESOURCE_NAME
- Loads handler_{resource_name}.py with FastAPI app
- Preserves all user routes and middleware
- Adds /ping health check endpoint

QB Endpoint Mode (FLASH_ENDPOINT_TYPE not set or not "lb"):
- Creates generic FastAPI app with /execute endpoint
- Uses RemoteExecutor for function execution
"""

import importlib.util
import logging
import os
from pathlib import Path
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
    return os.getenv("FLASH_ENDPOINT_TYPE") == "lb"


def _discover_lb_app(handler_dir: str = "/app") -> FastAPI:
    """Auto-discover and load the generated LB handler's FastAPI app.

    Derives handler path from FLASH_RESOURCE_NAME and imports the module.

    Args:
        handler_dir: Base directory for handler files (default /app).

    Returns:
        FastAPI app from the generated handler.

    Raises:
        RuntimeError: If FLASH_RESOURCE_NAME is not set or resolves outside handler_dir.
        FileNotFoundError: If the handler file does not exist.
        ImportError: If the handler module cannot produce a valid spec.
        AttributeError: If the handler module lacks an 'app' attribute.
        TypeError: If the 'app' attribute is not a FastAPI instance.
    """
    resource_name = os.getenv("FLASH_RESOURCE_NAME")
    if not resource_name:
        raise RuntimeError("FLASH_RESOURCE_NAME not set. Cannot discover generated LB handler.")

    handler_file = f"{handler_dir}/handler_{resource_name}.py"

    handler_path = Path(handler_file)
    if not handler_path.resolve().is_relative_to(Path(handler_dir).resolve()):
        raise RuntimeError(f"FLASH_RESOURCE_NAME '{resource_name}' resolves outside {handler_dir}")

    app_variable = "app"

    spec = importlib.util.spec_from_file_location("user_main", handler_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find or load {handler_file}")

    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)

    if not hasattr(user_module, app_variable):
        raise AttributeError(f"Module {handler_file} does not have '{app_variable}' attribute")

    discovered_app = getattr(user_module, app_variable)

    if not isinstance(discovered_app, FastAPI):
        raise TypeError(
            f"Expected FastAPI instance, got {type(discovered_app).__name__} for {app_variable}"
        )

    return discovered_app


is_lb_endpoint = _is_lb_endpoint()

if is_lb_endpoint:
    # LB endpoint mode: Auto-discover generated handler from FLASH_RESOURCE_NAME
    try:
        app = _discover_lb_app()
        logger.info("Successfully imported FastAPI app for LB endpoint")

        # Add /ping endpoint if not already present
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
        logger.error("Failed to initialize LB endpoint mode: %s", error, exc_info=True)
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
