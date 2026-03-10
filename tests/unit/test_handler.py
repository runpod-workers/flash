"""Tests for the RunPod handler function."""

import os
import sys

import pytest
import base64
import cloudpickle
from unittest.mock import patch, AsyncMock

# Clear deployed-mode env var before importing handler to prevent module-level
# _load_generated_handler() from raising when run outside a Docker container.
os.environ.pop("FLASH_RESOURCE_NAME", None)
sys.modules.pop("handler", None)

from handler import handler, _load_generated_handler  # noqa: E402
from runpod_flash.protos.remote_execution import FunctionResponse  # noqa: E402


class TestHandler:
    """Test cases for the RunPod handler function."""

    @pytest.mark.asyncio
    async def test_handler_success(self):
        """Test successful handler execution."""
        event = {
            "input": {
                "function_name": "test_func",
                "function_code": "def test_func(): return 'success'",
                "args": [],
                "kwargs": {},
            }
        }

        with patch("handler.RemoteExecutor") as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor
            mock_executor.ExecuteFunction.return_value = FunctionResponse(
                success=True,
                result=base64.b64encode(cloudpickle.dumps("success")).decode("utf-8"),
                stdout="Function executed successfully",
            )

            result = await handler(event)

            assert result["success"] is True
            assert "result" in result

    @pytest.mark.asyncio
    async def test_handler_invalid_input(self):
        """Test handler with invalid input data."""
        event = {
            "input": {
                # Missing required fields
                "args": [],
                "kwargs": {},
            }
        }

        result = await handler(event)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handler_missing_input(self):
        """Test handler with missing input key."""
        event = {}  # No input key

        result = await handler(event)

        # Should handle missing input gracefully
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handler_executor_exception(self):
        """Test handler when RemoteExecutor raises exception."""
        event = {
            "input": {
                "function_name": "test_func",
                "function_code": "def test_func(): return 'test'",
                "args": [],
                "kwargs": {},
            }
        }

        with patch("handler.RemoteExecutor") as mock_executor_class:
            mock_executor_class.side_effect = Exception("Executor initialization failed")

            result = await handler(event)

            assert result["success"] is False
            assert "Error in handler" in result["error"]
            assert "Executor initialization failed" in result["error"]

    @pytest.mark.asyncio
    async def test_handler_response_serialization(self):
        """Test that handler properly serializes FunctionResponse to dict."""
        event = {
            "input": {
                "function_name": "test_func",
                "function_code": "def test_func(): return {'data': 'test'}",
                "args": [],
                "kwargs": {},
            }
        }

        test_data = {"data": "test"}
        with patch("handler.RemoteExecutor") as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor
            mock_executor.ExecuteFunction.return_value = FunctionResponse(
                success=True,
                result=base64.b64encode(cloudpickle.dumps(test_data)).decode("utf-8"),
                stdout="Test output",
            )

            result = await handler(event)

            # Verify the response is properly serialized
            assert isinstance(result, dict)
            assert result["success"] is True
            assert "result" in result
            assert result["stdout"] == "Test output"

    @pytest.mark.asyncio
    async def test_handler_class_execution(self):
        """Test handler with class execution request."""
        event = {
            "input": {
                "execution_type": "class",
                "class_name": "TestClass",
                "class_code": "class TestClass:\n    def __call__(self): return 'class result'",
                "args": [],
                "kwargs": {},
            }
        }

        with patch("handler.RemoteExecutor") as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor
            mock_executor.ExecuteFunction.return_value = FunctionResponse(
                success=True,
                result=base64.b64encode(cloudpickle.dumps("class result")).decode("utf-8"),
                instance_id="TestClass_12345678",
                instance_info={"class_name": "TestClass", "method_calls": 1},
            )

            result = await handler(event)

            assert result["success"] is True
            assert "instance_id" in result
            assert "instance_info" in result


class TestLoadGeneratedHandler:
    """Test cases for _load_generated_handler delegation logic."""

    def test_returns_none_when_no_resource_name(self):
        """Without FLASH_RESOURCE_NAME, returns None (fallback to FunctionRequest)."""
        with patch.dict("os.environ", {}, clear=True):
            result = _load_generated_handler()
        assert result is None

    def test_raises_when_handler_file_missing(self, tmp_path):
        """With FLASH_RESOURCE_NAME but no handler file, raises RuntimeError."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path") as mock_path_cls:
                mock_path = mock_path_cls.return_value
                mock_path.exists.return_value = False
                mock_path.resolve.return_value = mock_path
                mock_path.is_relative_to.return_value = True
                with pytest.raises(RuntimeError, match="not found for resource"):
                    _load_generated_handler()

    def test_loads_generated_handler_from_file(self, tmp_path):
        """With valid generated handler file, loads and returns handler function."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text(
            "async def handler(event):\n"
            "    return {'result': event.get('input', {}).get('prompt', 'default')}\n"
        )

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                result = _load_generated_handler()

        assert result is not None
        assert callable(result)

    def test_raises_when_spec_creation_fails(self):
        """If importlib cannot create spec, raises RuntimeError."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path") as mock_path_cls:
                mock_path = mock_path_cls.return_value
                mock_path.exists.return_value = True
                mock_path.resolve.return_value = mock_path
                mock_path.is_relative_to.return_value = True
                with patch(
                    "handler.importlib.util.spec_from_file_location",
                    return_value=None,
                ):
                    with pytest.raises(RuntimeError, match="Failed to create module spec"):
                        _load_generated_handler()

    def test_raises_on_import_error_when_install_fails(self, tmp_path):
        """If install of missing package fails, raises with install failure message."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text(
            "from nonexistent_package import missing_function\ndef handler(event): pass\n"
        )

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                with patch("handler._try_install_missing_package", return_value=False):
                    with pytest.raises(RuntimeError, match="Failed to install"):
                        _load_generated_handler()

    def test_recovery_installs_missing_package_and_retries(self, tmp_path):
        """Successful on-the-fly install allows handler to load on retry."""
        from handler import _exec_handler_module

        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("def handler(event): return {'recovered': True}\n")

        import importlib.util

        spec = importlib.util.spec_from_file_location("handler_gpu_config", handler_file)
        assert spec is not None, f"Failed to create module spec for {handler_file}"
        assert spec.loader is not None, f"Module spec has no loader for {handler_file}"

        call_count = 0
        original_exec = spec.loader.exec_module

        def exec_side_effect(module):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ModuleNotFoundError("no module", name="fake_recovery_pkg")
            original_exec(module)

        with patch.object(spec.loader, "exec_module", side_effect=exec_side_effect):
            with patch("handler._try_install_missing_package", return_value=True) as mock_install:
                mod = _exec_handler_module(spec, handler_file)
                assert hasattr(mod, "handler")
                assert callable(mod.handler)
                mock_install.assert_called_once_with("fake_recovery_pkg")

    def test_recovery_stops_if_same_package_fails_twice(self, tmp_path):
        """If the same package keeps failing after install, raises immediately."""
        handler_file = tmp_path / "handler_gpu_config.py"
        # Always raises ModuleNotFoundError for same package, even after "install"
        handler_file.write_text("raise ModuleNotFoundError('still missing', name='stubborn_pkg')\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                with patch("handler._try_install_missing_package", return_value=True):
                    with pytest.raises(RuntimeError, match="still failing after attempted"):
                        _load_generated_handler()

    def test_raises_on_syntax_error(self, tmp_path):
        """SyntaxError in generated handler raises RuntimeError."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("def handler(event)\n")  # Missing colon

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                with pytest.raises(RuntimeError, match="syntax error"):
                    _load_generated_handler()

    def test_raises_on_generic_exception(self, tmp_path):
        """Generic exception during module load raises RuntimeError."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("raise RuntimeError('init failed')\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                with pytest.raises(RuntimeError, match="failed to load"):
                    _load_generated_handler()

    def test_raises_when_handler_attr_missing(self, tmp_path):
        """Module without 'handler' attribute raises RuntimeError."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("def not_a_handler(): pass\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                with pytest.raises(RuntimeError, match="no 'handler' function"):
                    _load_generated_handler()

    def test_raises_when_resource_name_has_path_traversal(self):
        """Path traversal in FLASH_RESOURCE_NAME raises RuntimeError."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "../../../etc/passwd"}):
            with pytest.raises(RuntimeError, match="resolves outside /app"):
                _load_generated_handler()

    def test_raises_when_handler_not_callable(self, tmp_path):
        """Non-callable 'handler' attribute raises RuntimeError."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("handler = 42\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                with pytest.raises(RuntimeError, match="not callable"):
                    _load_generated_handler()
