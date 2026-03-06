IMAGE = runpod/flash
TAG = $(or $(FLASH_IMAGE_TAG),local)
FULL_IMAGE = $(IMAGE):$(TAG)
FULL_IMAGE_CPU = $(IMAGE)-cpu:$(TAG)

# Detect host platform for local builds
ARCH := $(shell uname -m)
ifeq ($(ARCH),x86_64)
	PLATFORM := linux/amd64
else ifeq ($(ARCH),aarch64)
	PLATFORM := linux/arm64
else ifeq ($(ARCH),arm64)
	PLATFORM := linux/arm64
else
	PLATFORM := linux/amd64
endif

# WIP testing configuration (multi-platform builds)
WIP_TAG ?= wip
MULTI_PLATFORM := linux/amd64,linux/arm64

# Python version matrix for multi-version builds
GPU_PYTHON_VERSIONS := 3.11 3.12
CPU_PYTHON_VERSIONS := 3.10 3.11 3.12
DEFAULT_PYTHON_VERSION := 3.11

# PyTorch base image mapping per Python version (GPU only)
PYTORCH_BASE_3.11 := pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime
PYTORCH_BASE_3.12 := pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime

.PHONY: setup help

# Check if 'uv' is installed
ifeq (, $(shell which uv))
$(error "uv is not installed. Please install it before running this Makefile.")
endif

# Default target - show available commands
help: # Show this help menu
	@echo "Available make commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*# "; printf "%-20s %s\n", "Target", "Description"} /^[a-zA-Z_][a-zA-Z0-9_-]*:.*# / {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

dev: # Install development dependencies
	uv sync --all-groups

update: # Upgrade all dependencies
	uv sync --upgrade --all-groups
	uv lock --upgrade

clean: # Remove build artifacts and cache files
	rm -rf dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pkl" -delete

setup: dev # Initialize project and sync dependencies
	@echo "Setup complete. Development environment ready."

build: # Build both GPU and CPU Docker images
	make build-gpu
	make build-cpu
	make build-lb
	make build-lb-cpu

build-gpu: setup # Build GPU Docker image for host platform
	docker buildx build \
	--platform $(PLATFORM) \
	-t $(FULL_IMAGE) \
	. --load

build-cpu: setup # Build CPU-only Docker image for host platform
	docker buildx build \
	--platform $(PLATFORM) \
	-f Dockerfile-cpu \
	-t $(FULL_IMAGE_CPU) \
	. --load

build-lb: setup # Build Load Balancer Docker image for host platform
	docker buildx build \
	--platform $(PLATFORM) \
	-f Dockerfile-lb \
	-t $(IMAGE)-lb:$(TAG) \
	. --load

build-lb-cpu: setup # Build CPU-only Load Balancer Docker image for host platform
	docker buildx build \
	--platform $(PLATFORM) \
	-f Dockerfile-lb-cpu \
	-t $(IMAGE)-lb-cpu:$(TAG) \
	. --load

# WIP Build Targets (multi-platform, requires Docker Hub push)
# Usage: make build-wip
# Custom tag: make build-wip WIP_TAG=myname-feature
# Then deploy with: export FLASH_IMAGE_TAG=wip (or your custom tag)

build-wip: # Build and push all WIP images (multi-platform)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Building multi-platform WIP images with tag :$(WIP_TAG)"
	@echo "This will push to Docker Hub registry (requires docker login)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	make build-wip-gpu
	make build-wip-cpu
	make build-wip-lb
	make build-wip-lb-cpu
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ WIP images pushed to Docker Hub with tag :$(WIP_TAG)"
	@echo "Next steps:"
	@echo "  1. export FLASH_IMAGE_TAG=$(WIP_TAG)"
	@echo "  2. Deploy to RunPod and test"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

build-wip-gpu: setup # Build and push GPU image (multi-platform)
	docker buildx build \
	--platform $(MULTI_PLATFORM) \
	-t $(IMAGE):$(WIP_TAG) \
	. --push

build-wip-cpu: setup # Build and push CPU image (multi-platform)
	docker buildx build \
	--platform $(MULTI_PLATFORM) \
	-f Dockerfile-cpu \
	-t $(IMAGE)-cpu:$(WIP_TAG) \
	. --push

build-wip-lb: setup # Build and push LB image (multi-platform)
	docker buildx build \
	--platform $(MULTI_PLATFORM) \
	-f Dockerfile-lb \
	-t $(IMAGE)-lb:$(WIP_TAG) \
	. --push

build-wip-lb-cpu: setup # Build and push LB CPU image (multi-platform)
	docker buildx build \
	--platform $(MULTI_PLATFORM) \
	-f Dockerfile-lb-cpu \
	-t $(IMAGE)-lb-cpu:$(WIP_TAG) \
	. --push

# Versioned Build Targets (multi-Python-version matrix)
# GPU images: Python 3.11, 3.12 (with PyTorch base)
# CPU images: Python 3.10, 3.11, 3.12 (python:X.Y-slim)
# Tag format: py${VERSION}-${TAG} (e.g., runpod/flash:py3.11-local)

build-gpu-versioned: setup # Build GPU images for all GPU Python versions
	@pytorch_base() { \
		case "$$1" in \
			3.11) echo "$(PYTORCH_BASE_3.11)";; \
			3.12) echo "$(PYTORCH_BASE_3.12)";; \
		esac; \
	}; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		base=$$(pytorch_base $$pyver); \
		echo "Building GPU image for Python $$pyver (base: $$base)..."; \
		docker buildx build \
			--platform $(PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			--build-arg PYTORCH_BASE=$$base \
			-t $(IMAGE):py$$pyver-$(TAG) \
			. --load; \
	done

build-cpu-versioned: setup # Build CPU images for all CPU Python versions
	@for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo "Building CPU image for Python $$pyver..."; \
		docker buildx build \
			--platform $(PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			-f Dockerfile-cpu \
			-t $(IMAGE)-cpu:py$$pyver-$(TAG) \
			. --load; \
	done

build-lb-versioned: setup # Build GPU-LB images for all GPU Python versions
	@pytorch_base() { \
		case "$$1" in \
			3.11) echo "$(PYTORCH_BASE_3.11)";; \
			3.12) echo "$(PYTORCH_BASE_3.12)";; \
		esac; \
	}; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		base=$$(pytorch_base $$pyver); \
		echo "Building GPU-LB image for Python $$pyver (base: $$base)..."; \
		docker buildx build \
			--platform $(PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			--build-arg PYTORCH_BASE=$$base \
			-f Dockerfile-lb \
			-t $(IMAGE)-lb:py$$pyver-$(TAG) \
			. --load; \
	done

build-lb-cpu-versioned: setup # Build CPU-LB images for all CPU Python versions
	@for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo "Building CPU-LB image for Python $$pyver..."; \
		docker buildx build \
			--platform $(PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			-f Dockerfile-lb-cpu \
			-t $(IMAGE)-lb-cpu:py$$pyver-$(TAG) \
			. --load; \
	done

build-all-versioned: # Build all 10 versioned images (GPU+CPU, QB+LB)
	@echo "Building all versioned images (10 total)..."
	$(MAKE) build-gpu-versioned
	$(MAKE) build-cpu-versioned
	$(MAKE) build-lb-versioned
	$(MAKE) build-lb-cpu-versioned
	@echo "All 10 versioned images built."

# Versioned WIP Push Targets (multi-platform, requires Docker Hub push)
# Also tags DEFAULT_PYTHON_VERSION images as latest (unversioned tag)

build-wip-versioned: setup # Build and push all versioned images (multi-platform)
	@echo "Building and pushing all versioned images with tag prefix py*-$(WIP_TAG)..."
	@pytorch_base() { \
		case "$$1" in \
			3.11) echo "$(PYTORCH_BASE_3.11)";; \
			3.12) echo "$(PYTORCH_BASE_3.12)";; \
		esac; \
	}; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		base=$$(pytorch_base $$pyver); \
		echo "Pushing GPU QB image for Python $$pyver..."; \
		tag_args="-t $(IMAGE):py$$pyver-$(WIP_TAG)"; \
		if [ "$$pyver" = "$(DEFAULT_PYTHON_VERSION)" ]; then \
			tag_args="$$tag_args -t $(IMAGE):$(WIP_TAG)"; \
		fi; \
		docker buildx build \
			--platform $(MULTI_PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			--build-arg PYTORCH_BASE=$$base \
			$$tag_args \
			. --push; \
	done
	@for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo "Pushing CPU QB image for Python $$pyver..."; \
		tag_args="-t $(IMAGE)-cpu:py$$pyver-$(WIP_TAG)"; \
		if [ "$$pyver" = "$(DEFAULT_PYTHON_VERSION)" ]; then \
			tag_args="$$tag_args -t $(IMAGE)-cpu:$(WIP_TAG)"; \
		fi; \
		docker buildx build \
			--platform $(MULTI_PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			-f Dockerfile-cpu \
			$$tag_args \
			. --push; \
	done
	@pytorch_base() { \
		case "$$1" in \
			3.11) echo "$(PYTORCH_BASE_3.11)";; \
			3.12) echo "$(PYTORCH_BASE_3.12)";; \
		esac; \
	}; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		base=$$(pytorch_base $$pyver); \
		echo "Pushing GPU LB image for Python $$pyver..."; \
		tag_args="-t $(IMAGE)-lb:py$$pyver-$(WIP_TAG)"; \
		if [ "$$pyver" = "$(DEFAULT_PYTHON_VERSION)" ]; then \
			tag_args="$$tag_args -t $(IMAGE)-lb:$(WIP_TAG)"; \
		fi; \
		docker buildx build \
			--platform $(MULTI_PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			--build-arg PYTORCH_BASE=$$base \
			-f Dockerfile-lb \
			$$tag_args \
			. --push; \
	done
	@for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo "Pushing CPU LB image for Python $$pyver..."; \
		tag_args="-t $(IMAGE)-lb-cpu:py$$pyver-$(WIP_TAG)"; \
		if [ "$$pyver" = "$(DEFAULT_PYTHON_VERSION)" ]; then \
			tag_args="$$tag_args -t $(IMAGE)-lb-cpu:$(WIP_TAG)"; \
		fi; \
		docker buildx build \
			--platform $(MULTI_PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			-f Dockerfile-lb-cpu \
			$$tag_args \
			. --push; \
	done
	@echo "All versioned images pushed. Default ($(DEFAULT_PYTHON_VERSION)) also tagged as :$(WIP_TAG)."

# Versioned Smoke Tests

smoketest-versioned: build-all-versioned # Verify Python version in each versioned image
	@echo "Running Python version checks across all versioned images..."
	@fail=0; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		echo -n "GPU QB py$$pyver: "; \
		docker run --rm $(IMAGE):py$$pyver-$(TAG) python --version || fail=1; \
	done; \
	for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo -n "CPU QB py$$pyver: "; \
		docker run --rm $(IMAGE)-cpu:py$$pyver-$(TAG) python --version || fail=1; \
	done; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		echo -n "GPU LB py$$pyver: "; \
		docker run --rm $(IMAGE)-lb:py$$pyver-$(TAG) python --version || fail=1; \
	done; \
	for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo -n "CPU LB py$$pyver: "; \
		docker run --rm $(IMAGE)-lb-cpu:py$$pyver-$(TAG) python --version || fail=1; \
	done; \
	if [ $$fail -ne 0 ]; then echo "FAIL: Some images failed version check"; exit 1; fi; \
	echo "All 10 images passed Python version check."

# Test commands
test: # Run all tests in parallel
	uv run pytest tests/ -v -n auto --dist loadscope

test-unit: # Run unit tests only
	uv run pytest tests/unit/ -v -m "not integration" -n auto --dist loadscope

test-integration: # Run integration tests only
	uv run pytest tests/integration/ -v -m integration

test-coverage: # Run tests with coverage report (parallel)
	uv run pytest tests/ -v -n auto --dist loadscope --cov=handler --cov=remote_execution --cov-report=term-missing

test-fast: # Run tests with fast-fail mode
	uv run pytest tests/ -v -x --tb=short

test-handler: # Test handler locally with all test_*.json files
	cd src && ./test-handler.sh

test-lb-handler: # Test Load Balancer handler with /execute endpoint
	cd src && ./test-lb-handler.sh

# Smoke Tests (local Docker validation)

smoketest: build-gpu # Test Docker image locally
	docker run --rm $(FULL_IMAGE) ./test-handler.sh

smoketest-lb: build-lb # Test Load Balancer Docker image locally
	docker run --rm $(IMAGE)-lb:$(TAG) ./test-lb-handler.sh

smoketest-lb-cpu: build-lb-cpu # Test CPU-only Load Balancer Docker image locally
	docker run --rm $(IMAGE)-lb-cpu:$(TAG) ./test-lb-handler.sh

# Linting commands
lint: # Check code with ruff
	uv run ruff check .

lint-fix: # Fix code issues with ruff
	uv run ruff check . --fix

format: # Format code with ruff
	uv run ruff format .

format-check: # Check code formatting
	uv run ruff format --check .

# Type checking
typecheck: # Check types with mypy
	uv run mypy src/

# Quality gates (used in CI)
quality-check: format-check lint typecheck test-coverage test-handler

# Code intelligence commands
index: # Generate code intelligence index
	@echo "🔍 Indexing codebase..."
	@uv run python scripts/ast_to_sqlite.py

query: # Query symbols (usage: make query SYMBOL=name)
	@test -n "$(SYMBOL)" || (echo "Usage: make query SYMBOL=<name>" && exit 1)
	@uv run python scripts/code_intel.py find "$(SYMBOL)"

query-interface: # Show class interface (usage: make query-interface CLASS=ClassName)
	@test -n "$(CLASS)" || (echo "Usage: make query-interface CLASS=<ClassName>" && exit 1)
	@uv run python scripts/code_intel.py interface "$(CLASS)"

query-file: # Show file symbols (usage: make query-file FILE=path)
	@test -n "$(FILE)" || (echo "Usage: make query-file FILE=<path>" && exit 1)
	@uv run python scripts/code_intel.py file "$(FILE)"
