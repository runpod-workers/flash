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
# GPU base image (runpod/pytorch) is amd64-only — no arm64 manifest exists
GPU_PLATFORM := linux/amd64

# Python version matrix for multi-version builds
# GPU base image (runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2204) only supports 3.12
GPU_PYTHON_VERSION := 3.12
GPU_PYTHON_VERSIONS := 3.12
CPU_PYTHON_VERSIONS := 3.10 3.11 3.12
DEFAULT_PYTHON_VERSION := 3.12
PYTHON_VERSION ?= $(shell python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

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

build-gpu: setup # Build GPU Docker image (amd64 only)
	docker buildx build \
	--platform $(GPU_PLATFORM) \
	-t $(FULL_IMAGE) \
	. --load

build-cpu: setup # Build CPU-only Docker image for host platform
	docker buildx build \
	--platform $(PLATFORM) \
	-f Dockerfile-cpu \
	-t $(FULL_IMAGE_CPU) \
	. --load

build-lb: setup # Build GPU Load Balancer Docker image (amd64 only)
	docker buildx build \
	--platform $(GPU_PLATFORM) \
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

build-wip: # Build and push all WIP images (GPU fixed at 3.12, CPU at PYTHON_VERSION)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Building WIP images: GPU py$(GPU_PYTHON_VERSION), CPU py$(PYTHON_VERSION)"
	@echo "This will push to Docker Hub registry (requires docker login)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	$(MAKE) build-wip-gpu
	$(MAKE) build-wip-lb
	$(MAKE) build-wip-cpu PYTHON_VERSION=$(PYTHON_VERSION)
	$(MAKE) build-wip-lb-cpu PYTHON_VERSION=$(PYTHON_VERSION)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "WIP images pushed: GPU :py$(GPU_PYTHON_VERSION)-$(WIP_TAG), CPU :py$(PYTHON_VERSION)-$(WIP_TAG)"
	@echo "Next steps:"
	@echo "  1. export FLASH_IMAGE_TAG=$(WIP_TAG)"
	@echo "  2. Deploy to RunPod and test"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

build-wip-gpu: setup # Build and push GPU image (amd64 only)
	docker buildx build \
	--platform $(GPU_PLATFORM) \
	-t $(IMAGE):py$(GPU_PYTHON_VERSION)-$(WIP_TAG) \
	. --push

build-wip-cpu: setup # Build and push CPU image (multi-platform)
	docker buildx build \
	--platform $(MULTI_PLATFORM) \
	--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
	-f Dockerfile-cpu \
	-t $(IMAGE)-cpu:py$(PYTHON_VERSION)-$(WIP_TAG) \
	. --push

build-wip-lb: setup # Build and push GPU LB image (amd64 only)
	docker buildx build \
	--platform $(GPU_PLATFORM) \
	-f Dockerfile-lb \
	-t $(IMAGE)-lb:py$(GPU_PYTHON_VERSION)-$(WIP_TAG) \
	. --push

build-wip-lb-cpu: setup # Build and push LB CPU image (multi-platform)
	docker buildx build \
	--platform $(MULTI_PLATFORM) \
	--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
	-f Dockerfile-lb-cpu \
	-t $(IMAGE)-lb-cpu:py$(PYTHON_VERSION)-$(WIP_TAG) \
	. --push

# Versioned Build Targets (multi-Python-version matrix)
# GPU images: Python 3.12 only (runpod/pytorch base image pinned)
# CPU images: Python 3.10, 3.11, 3.12 (python:X.Y-slim)
# Tag format: py${VERSION}-${TAG} (e.g., runpod/flash:py3.12-local)

build-gpu-versioned: setup _build-gpu-versioned # Build GPU images for all GPU Python versions
_build-gpu-versioned:
	@for pyver in $(GPU_PYTHON_VERSIONS); do \
		echo "Building GPU image for Python $$pyver..."; \
		docker buildx build \
			--platform $(GPU_PLATFORM) \
			-t $(IMAGE):py$$pyver-$(TAG) \
			. --load; \
	done

build-cpu-versioned: setup _build-cpu-versioned # Build CPU images for all CPU Python versions
_build-cpu-versioned:
	@for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo "Building CPU image for Python $$pyver..."; \
		docker buildx build \
			--platform $(PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			-f Dockerfile-cpu \
			-t $(IMAGE)-cpu:py$$pyver-$(TAG) \
			. --load; \
	done

build-lb-versioned: setup _build-lb-versioned # Build GPU-LB images for all GPU Python versions
_build-lb-versioned:
	@for pyver in $(GPU_PYTHON_VERSIONS); do \
		echo "Building GPU-LB image for Python $$pyver..."; \
		docker buildx build \
			--platform $(GPU_PLATFORM) \
			-f Dockerfile-lb \
			-t $(IMAGE)-lb:py$$pyver-$(TAG) \
			. --load; \
	done

build-lb-cpu-versioned: setup _build-lb-cpu-versioned # Build CPU-LB images for all CPU Python versions
_build-lb-cpu-versioned:
	@for pyver in $(CPU_PYTHON_VERSIONS); do \
		echo "Building CPU-LB image for Python $$pyver..."; \
		docker buildx build \
			--platform $(PLATFORM) \
			--build-arg PYTHON_VERSION=$$pyver \
			-f Dockerfile-lb-cpu \
			-t $(IMAGE)-lb-cpu:py$$pyver-$(TAG) \
			. --load; \
	done

build-all-versioned: setup _build-gpu-versioned _build-cpu-versioned _build-lb-versioned _build-lb-cpu-versioned # Build all versioned images (GPU+CPU, QB+LB)
	@echo "All 8 versioned images built: $(words $(GPU_PYTHON_VERSIONS)) GPU x 2 modes + $(words $(CPU_PYTHON_VERSIONS)) CPU x 2 modes."

# Versioned WIP Push Targets (multi-platform, requires Docker Hub push)
# Also tags DEFAULT_PYTHON_VERSION images as latest (unversioned tag)

build-wip-versioned: setup # Build and push all versioned images (multi-platform)
	@echo "Building and pushing all versioned images with tag prefix py*-$(WIP_TAG)..."
	@for pyver in $(GPU_PYTHON_VERSIONS); do \
		echo "Pushing GPU QB image for Python $$pyver..."; \
		tag_args="-t $(IMAGE):py$$pyver-$(WIP_TAG)"; \
		if [ "$$pyver" = "$(DEFAULT_PYTHON_VERSION)" ]; then \
			tag_args="$$tag_args -t $(IMAGE):$(WIP_TAG)"; \
		fi; \
		docker buildx build \
			--platform $(GPU_PLATFORM) \
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
	@for pyver in $(GPU_PYTHON_VERSIONS); do \
		echo "Pushing GPU LB image for Python $$pyver..."; \
		tag_args="-t $(IMAGE)-lb:py$$pyver-$(WIP_TAG)"; \
		if [ "$$pyver" = "$(DEFAULT_PYTHON_VERSION)" ]; then \
			tag_args="$$tag_args -t $(IMAGE)-lb:$(WIP_TAG)"; \
		fi; \
		docker buildx build \
			--platform $(GPU_PLATFORM) \
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
	check_version() { \
		label="$$1"; image="$$2"; pyver="$$3"; \
		echo -n "$$label py$$pyver: "; \
		out=$$(docker run --rm $$image python --version 2>&1) || { echo "docker run failed"; fail=1; return; }; \
		case "$$out" in \
			Python\ $$pyver*) echo "$$out" ;; \
			*) echo "Version mismatch (expected $$pyver): $$out"; fail=1 ;; \
		esac; \
	}; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		check_version "GPU QB" "$(IMAGE):py$$pyver-$(TAG)" "$$pyver"; \
	done; \
	for pyver in $(CPU_PYTHON_VERSIONS); do \
		check_version "CPU QB" "$(IMAGE)-cpu:py$$pyver-$(TAG)" "$$pyver"; \
	done; \
	for pyver in $(GPU_PYTHON_VERSIONS); do \
		check_version "GPU LB" "$(IMAGE)-lb:py$$pyver-$(TAG)" "$$pyver"; \
	done; \
	for pyver in $(CPU_PYTHON_VERSIONS); do \
		check_version "CPU LB" "$(IMAGE)-lb-cpu:py$$pyver-$(TAG)" "$$pyver"; \
	done; \
	if [ $$fail -ne 0 ]; then echo "FAIL: Some images failed version check"; exit 1; fi; \
	echo "All versioned images passed Python version check."

# Test commands
test: # Run all tests in parallel
	uv run pytest tests/ -v -n auto --dist loadscope

test-unit: # Run unit tests only
	uv run pytest tests/unit/ -v -m "not integration" -n auto --dist loadscope

test-integration: # Run integration tests only
	uv run pytest tests/integration/ -v -m integration

test-coverage: # Run tests with coverage report (parallel)
	uv run pytest tests/ -v -n auto --dist loadscope --cov=handler --cov=remote_execution --cov-branch --cov-report=term-missing --cov-report=xml --junitxml=pytest-results.xml

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

check-deps: # Reject git-ref dependencies in pyproject.toml
	uv run python scripts/check_git_deps.py

# Quality gates (used in CI)
quality-check: format-check lint typecheck check-deps test-coverage test-handler

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
