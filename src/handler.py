import importlib.util
import logging
import os
import sys
import uuid
from pathlib import Path
from collections.abc import Awaitable
from typing import Any, Dict, Optional

from constants import MAX_IMPORT_RECOVERY_ATTEMPTS
from logger import setup_logging, set_request_id, reset_request_id
from unpack_volume import maybe_unpack
from version import format_version_banner

# Initialize logging configuration
setup_logging()

logger = logging.getLogger(__name__)

# Unpack Flash deployment artifacts if running in Flash mode
# This is a no-op for Live Serverless and local development
maybe_unpack()

# Log after unpack so bundled runpod_flash is on sys.path
logger.info(format_version_banner())

def _extract_request_id(event: Dict[str, Any]) -> str:
    """Extract RunPod job id from event, with safe fallback."""
    event_id = event.get("id")
    if isinstance(event_id, str) and event_id.strip():
        return event_id

    job_id = event.get("job_id")
    if isinstance(job_id, str) and job_id.strip():
        return job_id

    job = event.get("job")
    if isinstance(job, dict):
        nested_job_id = job.get("id")
        if isinstance(nested_job_id, str) and nested_job_id.strip():
            return nested_job_id

    return str(uuid.uuid4())

def _is_deployed_mode() -> bool:
    """True when running as a Flash-deployed endpoint (not Live Serverless)."""
    return bool(os.getenv("FLASH_RESOURCE_NAME"))


class _HandlerRecoveryError(RuntimeError):
    """Raised by _exec_handler_module when on-the-fly recovery fails.

    Distinguished from generic RuntimeError so _load_generated_handler can
    re-raise it without wrapping, while still wrapping user-code RuntimeErrors.
    """


def _extract_missing_package(error: ImportError) -> str | None:
    """Extract the top-level package name from an ImportError.

    Returns the root package name (e.g. 'numpy' from 'numpy.core') or None
    if the module name cannot be determined.
    """
    module_name: str | None = getattr(error, "name", None)
    if not module_name:
        return None
    return module_name.split(".")[0]


def _try_install_missing_package(package_name: str) -> bool:
    """Attempt to install a missing package on-the-fly via DependencyInstaller.

    Returns True if installation succeeded, False otherwise.
    """
    from dependency_installer import DependencyInstaller

    installer = DependencyInstaller()
    result = installer.install_dependencies([package_name])
    return bool(result.success)


def _exec_handler_module(
    spec: importlib.machinery.ModuleSpec,
    handler_file: Path,
) -> Any:
    """Execute a handler module spec, installing missing packages on-the-fly.

    When a deployed handler fails to import due to a missing package (e.g.
    numpy excluded from the build artifact but needed at runtime), this
    function installs the package and retries. This adds to cold start time
    but prevents a fatal crash.

    Returns:
        The loaded module object.

    Raises:
        _HandlerRecoveryError: If the handler cannot be loaded after recovery attempts.
    """
    installed_packages: list[str] = []

    for _attempt in range(MAX_IMPORT_RECOVERY_ATTEMPTS + 1):
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod
        except ModuleNotFoundError as e:
            if len(installed_packages) >= MAX_IMPORT_RECOVERY_ATTEMPTS:
                raise _HandlerRecoveryError(
                    f"Generated handler {handler_file} failed to load after "
                    f"installing {len(installed_packages)} missing packages: "
                    f"{installed_packages}. Too many missing dependencies — "
                    f"redeploy with 'flash deploy'."
                ) from e

            package_name = _extract_missing_package(e)
            if not package_name or package_name in installed_packages:
                raise _HandlerRecoveryError(
                    "Import is still failing after attempted automatic recovery "
                    "or the missing dependency could not be determined. "
                    "Inspect your handler and its dependencies, then redeploy "
                    "with 'flash deploy'."
                ) from e

            logger.warning(
                "Package '%s' is not in the build artifact. Installing on-the-fly. "
                "This adds to cold start time — consider adding it to your "
                "dependencies list to include it in the build artifact.",
                package_name,
            )

            if not _try_install_missing_package(package_name):
                raise _HandlerRecoveryError(
                    f"Failed to install missing package '{package_name}'. "
                    f"Generated handler {handler_file} cannot be loaded. "
                    f"Redeploy with 'flash deploy'."
                ) from e

            installed_packages.append(package_name)
            # Clear the failed module from sys.modules so the retry gets a fresh import
            for key in list(sys.modules):
                if key == package_name or key.startswith(f"{package_name}."):
                    del sys.modules[key]
            importlib.invalidate_caches()
            logger.info("Installed '%s', retrying handler load", package_name)

    raise _HandlerRecoveryError(
        f"Generated handler {handler_file} failed to load after installing "
        f"{len(installed_packages)} missing packages: {installed_packages}. "
        f"Too many missing dependencies — redeploy with 'flash deploy'."
    )


def _load_generated_handler() -> Optional[Any]:
    """Load Flash-generated handler for deployed QB mode.

    Checks for a handler_<resource_name>.py file generated by the flash
    build pipeline. These handlers accept plain JSON input without
    FunctionRequest/cloudpickle serialization.

    If the handler fails to import due to a missing package, attempts
    on-the-fly installation before giving up. This handles cases where
    a package was excluded from the build artifact (e.g. size-prohibitive
    packages) but is needed at runtime.

    In deployed mode (FLASH_RESOURCE_NAME set), failures are fatal.
    FunctionRequest fallback is only valid for Live Serverless workers.

    Returns:
        Handler function if generated handler found, None if not in
        deployed mode.

    Raises:
        RuntimeError: If in deployed mode and the handler cannot be loaded.
    """
    resource_name = os.getenv("FLASH_RESOURCE_NAME")
    if not resource_name:
        return None

    handler_file = Path(f"/app/handler_{resource_name}.py")

    if not handler_file.resolve().is_relative_to(Path("/app").resolve()):
        raise RuntimeError(
            f"FLASH_RESOURCE_NAME '{resource_name}' resolves outside /app. "
            f"This is a security violation. Check the endpoint environment variables."
        )

    if not handler_file.exists():
        raise RuntimeError(
            f"Generated handler {handler_file} not found for resource '{resource_name}'. "
            f"The build artifact is incomplete. Redeploy with 'flash deploy'."
        )

    spec = importlib.util.spec_from_file_location(f"handler_{resource_name}", handler_file)
    if not spec or not spec.loader:
        raise RuntimeError(
            f"Failed to create module spec for {handler_file}. "
            f"The file may be corrupted. Redeploy with 'flash deploy'."
        )

    try:
        mod = _exec_handler_module(spec, handler_file)
    except SyntaxError as e:
        raise RuntimeError(
            f"Generated handler {handler_file} has a syntax error: {e}. "
            f"This indicates a bug in the flash build pipeline."
        ) from e
    except _HandlerRecoveryError:
        # Recovery-specific RuntimeErrors from _exec_handler_module — already formatted
        raise
    except Exception as e:
        raise RuntimeError(
            f"Generated handler {handler_file} failed to load: {e} ({type(e).__name__}). "
            f"Redeploy with 'flash deploy'."
        ) from e

    generated = getattr(mod, "handler", None)
    if generated is None:
        raise RuntimeError(
            f"Generated handler {handler_file} has no 'handler' function. "
            f"This indicates a bug in the flash build pipeline."
        )

    if not callable(generated):
        raise RuntimeError(
            f"Generated handler {handler_file} has a 'handler' attribute "
            f"but it is not callable ({type(generated).__name__}). "
            f"This indicates a bug in the flash build pipeline."
        )

    logger.info("Loaded generated handler from %s", handler_file)
    return generated


# Deployed mode: generated handler is mandatory, failures are fatal.
# Live Serverless mode: FunctionRequest handler is the only path.
if _is_deployed_mode():
    _generated = _load_generated_handler()

    async def handler(event: Dict[str, Any]) -> Dict[str, Any]:
        request_id_token = set_request_id(_extract_request_id(event))
        try:
            result = _generated(event)
            if isinstance(result, Awaitable):
                return await result
            return result
        finally:
            reset_request_id(request_id_token)

else:
    from runpod_flash.protos.remote_execution import FunctionRequest, FunctionResponse
    from remote_executor import RemoteExecutor

    async def handler(event: Dict[str, Any]) -> Dict[str, Any]:
        """RunPod serverless handler for Live Serverless (FunctionRequest protocol)."""
        output: FunctionResponse
        request_id_token = set_request_id(_extract_request_id(event))

        try:
            executor = RemoteExecutor()
            input_data = FunctionRequest(**event.get("input", {}))
            output = await executor.ExecuteFunction(input_data)

        except Exception as error:
            output = FunctionResponse(
                success=False,
                error=f"Error in handler: {str(error)}",
            )
        finally:
            reset_request_id(request_id_token)

        return output.model_dump()  # type: ignore[no-any-return]


# Start the RunPod serverless handler (only available on RunPod platform)
if __name__ == "__main__":
    import runpod

    runpod.serverless.start({"handler": handler})
