# Base image (runpod/pytorch:ubuntu2204) ships Ubuntu 22.04 system python3.10
# plus alt-Python interpreters for 3.11/3.12 with torch pre-installed on 3.12.
# For non-3.12 targets we reinstall torch from the CUDA 12.8 wheel index
# (~7 GB overhead) and repoint /usr/local/bin/python so the worker CMD picks
# up the correct interpreter.
# Base image provides Python 3.9-3.13 via deadsnakes; only 3.12 has torch
# pre-installed. For 3.10 and 3.11 we reinstall torch from the CUDA 12.8
# wheel index (~7 GB overhead) and repoint /usr/local/bin/python so the
# worker CMD picks up the correct interpreter.
FROM runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2204

# Target Python version for the worker runtime.
ARG PYTHON_VERSION=3.12
ARG TORCH_VERSION=2.9.1+cu128
# torchvision is NOT shipped by the runpod/pytorch base image (unlike torch and
# torchaudio) and is auto-excluded from Flash build tarballs, so it must be
# installed here. Pin to the release paired with TORCH_VERSION (torch 2.9.1 ->
# torchvision 0.24.1); update both together on a torch bump. See SLS-377.
ARG TORCHVISION_VERSION=0.24.1
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128

# Expose the target version to the running worker for startup validation.
ENV FLASH_PYTHON_VERSION=${PYTHON_VERSION}

# Validate the base image provides the requested interpreter and activate it.
# For non-3.12 targets, install torch for the selected Python and repoint
# /usr/local/bin/python and python3 so downstream `python` invocations use it.
# For 3.12 we keep the base image's python/torch untouched to avoid the
# ~7 GB reinstall cost.
#
# pip bootstrap: Ubuntu 22.04's system python3.10 has ensurepip disabled by
# Debian policy, so we install pip via get-pip.py (works for any interpreter
# regardless of distro patching). urllib is stdlib, avoiding a curl dependency.
RUN python${PYTHON_VERSION} --version \
 && if [ "${PYTHON_VERSION}" != "3.12" ]; then \
      python${PYTHON_VERSION} -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', '/tmp/get-pip.py')" \
      && python${PYTHON_VERSION} /tmp/get-pip.py --no-cache-dir \
      && rm -f /tmp/get-pip.py \
RUN python${PYTHON_VERSION} --version \
 && if [ "${PYTHON_VERSION}" != "3.12" ]; then \
      python${PYTHON_VERSION} -m ensurepip --upgrade \
      && python${PYTHON_VERSION} -m pip install --no-cache-dir \
           --index-url ${TORCH_INDEX_URL} \
           "torch==${TORCH_VERSION}" \
      && ln -sf "$(which python${PYTHON_VERSION})" /usr/local/bin/python \
      && ln -sf "$(which python${PYTHON_VERSION})" /usr/local/bin/python3; \
    fi

WORKDIR /app

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
# Set timezone to avoid tzdata prompts
ENV TZ=Etc/UTC

# Enable HuggingFace transfer acceleration
ENV HF_HUB_ENABLE_HF_TRANSFER=1
# Relocate HuggingFace cache outside /root/.cache to exclude from volume sync
ENV HF_HOME=/hf-cache

# Configure APT cache to persist under /root/.cache for volume sync
RUN mkdir -p /root/.cache/apt/archives/partial \
 && echo 'Dir::Cache "/root/.cache/apt";' > /etc/apt/apt.conf.d/01cache

# Install system dependencies and uv
# Note: build-essential not pre-installed to reduce image size (400MB savings)
# Automatic detection will install it when needed (no manual action required)
# Advanced: Users can pre-install via system_dependencies=["build-essential"]
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && cp ~/.local/bin/uv /usr/local/bin/uv \
 && chmod +x /usr/local/bin/uv \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Copy app code and install dependencies
# Use --python to target the active interpreter (preserves torch in its site-packages)
COPY README.md pyproject.toml uv.lock ./
COPY src/ ./
RUN uv export --format requirements-txt --no-dev --no-hashes > requirements.txt \
 && uv pip install --python $(which python) --break-system-packages -r requirements.txt

# Install numpy for the active Python version.
# The runpod/pytorch image ships torch but not numpy. Flash build excludes numpy
# from tarballs (BASE_IMAGE_PACKAGES) to save tarball space (~30 MB), so numpy
# must be provided here in the base image.
RUN python -m pip install --no-cache-dir numpy

# Install torchvision for the active Python version.
# The runpod/pytorch base ships torch/torchaudio but NOT torchvision, and Flash
# build auto-excludes torchvision from tarballs, so it must be provided here.
# Use the CUDA wheel index to stay aligned with the base image torch build.
RUN python -m pip install --no-cache-dir \
      --index-url ${TORCH_INDEX_URL} \
      "torchvision==${TORCHVISION_VERSION}"

# Verify torch, torchvision, numpy, and the expected Python version are available.
RUN python -c "import sys; actual = f'{sys.version_info.major}.{sys.version_info.minor}'; expected = '${PYTHON_VERSION}'; assert actual == expected, f'Expected Python {expected}, got {actual}'; print(f'Python {actual} OK')" \
 && python -c "import torch; print(f'torch {torch.__version__} CUDA {torch.cuda.is_available()}')" \
 && python -c "import torchvision; print(f'torchvision {torchvision.__version__}')" \
 && python -c "import numpy; print(f'numpy {numpy.__version__}')"

CMD ["python", "handler.py"]
