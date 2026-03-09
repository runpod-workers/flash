# Base image provides Python 3.12 (from runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2204)
FROM runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2204

# Use the base image's Python as-is to preserve pre-installed packages (torch, cuda libs).
# The pytorch base image provides its own Python with torch already installed.
# Symlinking to /usr/bin/python3.X would switch to a bare system Python without torch.
RUN python --version

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
# Use --python to target the base image's Python (preserves torch in its site-packages)
COPY README.md pyproject.toml uv.lock ./
COPY src/ ./
RUN uv export --format requirements-txt --no-dev --no-hashes > requirements.txt \
 && uv pip install --python $(which python) --break-system-packages -r requirements.txt

# Install numpy for the base image's Python version.
# The runpod/pytorch image ships torch but not numpy. Flash build excludes numpy
# from tarballs (BASE_IMAGE_PACKAGES) to save tarball space (~30 MB), so numpy
# must be provided here in the base image.
RUN pip install --no-cache-dir numpy

# Verify torch and numpy are available from the base image
RUN python -c "import torch; print(f'torch {torch.__version__} CUDA {torch.cuda.is_available()}')" \
 && python -c "import numpy; print(f'numpy {numpy.__version__}')"

CMD ["python", "handler.py"]
