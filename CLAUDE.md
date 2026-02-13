# worker-flash - RunPod Serverless Worker

RunPod Serverless worker template providing dynamic GPU provisioning for ML workloads with transparent execution and persistent workspace management.

## Components

1. **RunPod Worker Handler** (`src/handler.py`) - Serverless function executing remote Python with dependency management
2. **Flash SDK** (pip dependency) - Python library for distributed inference and ML model serving

## Key Areas

### 1. Remote Function Execution (`src/`)
- **Core Handler** (`src/handler.py:18`) - Main RunPod serverless entry point
- **Remote Executor** (`src/remote_executor.py:11`) - Central orchestrator using composition pattern
- **Function Executor** (`src/function_executor.py:12`) - Function execution with full output capture
- **Class Executor** (`src/class_executor.py:14`) - Class instantiation and method execution with instance persistence

### 2. Dependency Management (`src/dependency_installer.py:14`)
- **Python Packages**: UV-based with environment-aware config (Docker vs local)
- **System Packages**: APT/Nala-based with acceleration support
- **Differential Installation**: Skips already-installed packages
- **Environment Detection**: Automatic Docker vs local detection

### 3. Universal Subprocess (`src/subprocess_utils.py`)
- Centralized subprocess operations via `run_logged_subprocess`
- Automatic logging integration (all output flows through log streamer at DEBUG)
- Environment-aware execution
- Standardized error handling with FunctionResponse
- Configurable timeouts with cleanup

### 4. Serialization & Protocol (`runpod_flash.protos.remote_execution`)
- **Protocol Definitions**: Pydantic models for request/response with validation
- **Serialization Utils** (`src/serialization_utils.py`): CloudPickle-based data serialization
- **Base Executor** (`src/base_executor.py`): Common execution interface

### 5. Flash SDK Integration (pip dependency)
- Installation: pip from GitHub
- Client Interface: `@remote` decorator for remote execution
- Resource Management: GPU/CPU configuration via LiveServerless
- Repository: https://github.com/runpod/flash

### 6. Testing (`tests/`)
- **Unit Tests** (`tests/unit/`) - Component-level with mocking
- **Integration Tests** (`tests/integration/`) - End-to-end workflows
- **Test Fixtures** (`tests/conftest.py:1`) - Shared test data and utilities
- **Handler Testing**: Local validation with JSON test files (`src/tests/`)

### 7. Build & Deployment
- **Docker**: GPU (`Dockerfile`) and CPU (`Dockerfile-cpu`) images
- **CI/CD**: Automated testing, linting, releases (`.github/workflows/`)
- **Quality Gates** (`Makefile:104`): Format, type checking, coverage requirements
- **Release Management**: Automated semantic versioning and Docker Hub deployment

### 8. Configuration (`src/constants.py`)
- System-wide constants (NAMESPACE, LARGE_SYSTEM_PACKAGES)
- Environment configuration for RunPod API

## Architecture

### Core Components

**`src/handler.py`**: Main RunPod serverless handler
- Executes arbitrary Python functions remotely with workspace support
- Dynamic installation of Python and system dependencies with differential updates
- Serialization/deserialization with cloudpickle
- Captures stdout, stderr, and logs from execution

**`runpod_flash.protos.remote_execution`**: Protocol definitions
- `FunctionRequest`: Function execution requests with dependencies
- `FunctionResponse`: Standardized response format with success/error handling
- Imported from installed runpod-flash package

### Key Patterns

1. **Remote Function Execution**: Functions with `@remote` executed on RunPod GPU workers
2. **Composition Pattern**: RemoteExecutor uses specialized components
3. **Dynamic Dependency Management**: Dependencies installed at runtime with differential updates
4. **Universal Subprocess**: All subprocess calls use centralized `run_logged_subprocess`
5. **Environment-Aware Config**: Automatic Docker vs local detection
6. **Serialization**: CloudPickle + base64 for function args and results
7. **Resource Configuration**: `LiveServerless` defines GPU requirements and scaling

## MCP Code Intelligence

worker-flash-code-intel MCP server configured for efficient exploration.

### Indexed Codebase
- **Project source** (`src/`) - All 83 worker-flash symbols
- **runpod_flash dependency** - All 552 protocol definitions, resources, and core components

To regenerate index (when dependencies change): `make index`

To add more dependencies: Edit `DEPENDENCIES_TO_INDEX` in `scripts/ast_to_sqlite.py`

### MCP Tools

**Always prefer MCP over Grep/Glob for semantic searches:**

- `find_symbol(symbol)` - Find classes, functions, methods by name
- `list_classes()` - Get all classes in codebase
- `get_class_interface(class_name)` - Get class methods without implementations
- `list_file_symbols(file_path)` - List symbols in specific file
- `find_by_decorator(decorator)` - Find decorated functions/classes

### Tool Selection
- **MCP**: Semantic searches (class names, function definitions, decorators, symbols) - including runpod_flash
- **Grep**: Content searches (error messages, comments, strings, logs)
- **Glob**: File path patterns when you know structure
- **Task(Explore)**: Complex multi-step exploration

## Commands

### Setup
```bash
make setup                    # Initialize project and sync dependencies
make dev                      # Install dev dependencies (pytest, ruff)
uv sync                      # Sync production dependencies
uv sync --all-groups         # Sync all groups (same as make dev)
```

### Code Quality
```bash
make lint                     # Check with ruff
make lint-fix                # Auto-fix linting
make format                   # Format with ruff
make format-check            # Check formatting
make quality-check           # All checks (format, lint, test coverage)
```

### Testing
```bash
make test                     # Run all tests
make test-unit               # Unit tests only
make test-integration        # Integration tests only
make test-coverage           # Tests with coverage report
make test-fast               # Fail-fast mode
make test-handler            # Test handler with all test_*.json files
```

### Docker
```bash
make build                    # Build GPU image (linux/amd64)
make build-cpu               # Build CPU-only image
```

## Configuration

### Environment Variables
- `RUNPOD_API_KEY` - Required for RunPod Serverless
- `RUNPOD_ENDPOINT_ID` - Workspace isolation (auto-set by RunPod)
- `HF_HUB_ENABLE_HF_TRANSFER` - Set to "1" for accelerated HuggingFace downloads
- `HF_TOKEN` - Optional auth for private/gated HuggingFace models
- `HF_HOME=/hf-cache` - HuggingFace cache location (outside `/root/.cache`)
- `DEBIAN_FRONTEND=noninteractive` - Set during system package installation

### Resource Configuration
```python
gpu_config = LiveServerless(
    name="my-endpoint",           # Endpoint name
    gpus=[GpuGroup.ANY],         # GPU types
    workersMax=5,                # Max concurrent workers
    workersMin=0,                # Min workers (0 = scale to zero)
    idleTimeout=5,               # Minutes before scaling down
    executionTimeoutMs=600000,   # Max execution time
)
```

## Testing

- **pytest** with coverage and async support
- **Unit tests** (`tests/unit/`) - Test components in isolation
- **Integration tests** (`tests/integration/`) - End-to-end workflows
- **Coverage target**: 35% minimum with HTML/XML reports
- **Test fixtures**: Shared data and mocks in `tests/conftest.py`
- **CI Integration**: Tests run on all PRs and before releases

## Development Notes

### Dependency Management
- Root project uses `uv` with `pyproject.toml`
- Runpod Flash SDK installed as pip dependency from GitHub
- System dependencies via `apt-get` in containers
- Python dependencies via `uv pip install` at runtime
- **Differential Installation**: Only installs missing packages
- **Environment Awareness**: Docker: `--python-preference=only-system`, Local: managed python

### Error Handling
- All remote execution wrapped in try/catch with full traceback
- Structured error responses via `FunctionResponse.error`
- Combined stdout/stderr/log capture

### Security
- Functions execute arbitrary Python in sandboxed containers
- System package installation requires root in container
- No secrets in repository
- API keys via environment variables

## File Structure
```
src/
├── handler.py            # Main serverless handler
├── remote_executor.py    # Central orchestrator
├── function_executor.py  # Function execution with output
├── class_executor.py     # Class execution with persistence
├── dependency_installer.py # Python and system deps
├── serialization_utils.py # CloudPickle serialization
├── base_executor.py      # Common execution interface
├── constants.py          # System constants
└── tests/                # Handler test JSON files
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
└── integration/         # Integration tests
```

## CI/CD

### Automated Releases
- Uses `release-please` for automated semantic versioning
- Releases triggered by conventional commits on `main`
- Docker images auto-built and pushed to Docker Hub (`runpod/flash`) on release

### GitHub Actions (`.github/workflows/ci.yml`)
- Tests and linting on PRs and main pushes
- **Local execution testing**: Validates all `test_*.json` files
- Manages releases via `release-please` on main
- Builds and pushes `:main` tagged images on main pushes
- Builds production images with semantic versioning on releases
- Manual triggering via `workflow_dispatch`

### Required Secrets
- `DOCKERHUB_USERNAME` - Docker Hub username
- `DOCKERHUB_TOKEN` - Docker Hub password/token

## Development Best Practices

- Run `make quality-check` before committing
- Use `git mv` when moving files
- Run `make test-handler` to validate handler
- Never create files unless necessary
- Prefer editing existing files over creating new ones
- Never proactively create documentation unless requested

## Branch Info
- Main: `main`
- Current: `tmp/deployed-execution`
