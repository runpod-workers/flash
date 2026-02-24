"""Tests for the RunPod handler function."""

import pytest
import base64
import cloudpickle
from unittest.mock import patch, AsyncMock
from handler import handler, _load_generated_handler
from runpod_flash.protos.remote_execution import FunctionResponse


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

    def test_logs_warning_when_handler_file_missing(self, tmp_path):
        """With FLASH_RESOURCE_NAME but no handler file, logs warning and returns None."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path") as mock_path_cls:
                mock_path = mock_path_cls.return_value
                mock_path.exists.return_value = False
                result = _load_generated_handler()
        assert result is None

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

    def test_returns_none_when_spec_creation_fails(self):
        """If importlib cannot create spec, returns None."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path") as mock_path_cls:
                mock_path = mock_path_cls.return_value
                mock_path.exists.return_value = True
                with patch(
                    "handler.importlib.util.spec_from_file_location",
                    return_value=None,
                ):
                    result = _load_generated_handler()

        assert result is None

    def test_returns_none_on_import_error(self, tmp_path):
        """If generated handler has ImportError, falls back gracefully."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text(
            "from nonexistent_package import missing_function\ndef handler(event): pass\n"
        )

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                result = _load_generated_handler()

        assert result is None

    def test_returns_none_on_syntax_error(self, tmp_path):
        """SyntaxError in generated handler logs error and returns None."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("def handler(event)\n")  # Missing colon

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                result = _load_generated_handler()

        assert result is None

    def test_returns_none_on_generic_exception(self, tmp_path):
        """Generic exception during module load falls back gracefully."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("raise RuntimeError('init failed')\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                result = _load_generated_handler()

        assert result is None

    def test_warns_when_handler_attr_missing(self, tmp_path):
        """Module without 'handler' attribute logs warning and returns None."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("def not_a_handler(): pass\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                result = _load_generated_handler()

        assert result is None

    def test_returns_none_when_resource_name_has_path_traversal(self):
        """Path traversal in FLASH_RESOURCE_NAME returns None."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "../../../etc/passwd"}):
            result = _load_generated_handler()
        assert result is None

    def test_returns_none_when_handler_not_callable(self, tmp_path):
        """Non-callable 'handler' attribute returns None."""
        handler_file = tmp_path / "handler_gpu_config.py"
        handler_file.write_text("handler = 42\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "gpu_config"}):
            with patch("handler.Path", return_value=handler_file):
                result = _load_generated_handler()

        assert result is None
