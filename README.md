![RunPod Worker Template](https://cpjrphpz3t5wbwfe.public.blob.vercel-storage.com/worker-template_banner-zUuCAjwDuvfsINR6vKBhYvvm3TnZFB.jpeg)

---

This repository serves as a starting point for creating your own custom RunPod Serverless worker. It provides a basic structure and configuration that you can build upon.

---

[![RunPod](https://api.runpod.io/badge/runpod-workers/flash)](https://www.runpod.io/console/hub/runpod-workers/flash)

---

## Getting Started

1.  **Use this template:** Create a new repository based on this template or clone it directly.
2.  **Customize:** Modify the code and configuration files to implement your specific task.
3.  **Test:** Run your worker locally to ensure it functions correctly.
4.  **Deploy:** Connect your repository to RunPod or build and push the Docker image manually.

## Python Version Support

### GPU Images: Python 3.12 Only

The GPU base image (`runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2204`) installs multiple Python interpreters (3.9-3.14) via the deadsnakes PPA, but torch and CUDA-linked packages are only installed for Python 3.12. The `python` symlink points to 3.12. The other interpreters exist for interactive pod and notebook use cases, not for serverless workers.

Using a different Python version in a GPU worker would require reinstalling torch (~2GB) and ensuring all C-extension wheels (numpy, Pillow, etc.) match the interpreter's ABI. This is not supported by the build pipeline.

### CPU Images: Python 3.10, 3.11, 3.12

CPU images use `python:X.Y-slim` base images where the Python version is configurable via the `PYTHON_VERSION` build arg. Any of 3.10, 3.11, or 3.12 can be used.

### Build Pipeline

`flash build` automatically downloads wheels for the container's Python version (3.12 for GPU), regardless of the build machine's local Python. Users do not need to configure this.

### Image Tag Format

Image tags follow the pattern `py{version}-{tag}` (e.g., `runpod/flash:py3.12-latest`).

## Customizing Your Worker

- **`handler.py`:** This is the core of your worker.
  - The `handler(event)` function is the entry point executed for each job.
  - The `event` dictionary contains the job input under the `"input"` key.
  - Modify this function to load your models, process the input and return the desired output.
  - Consider implementing model loading outside the handler (e.g., globally or in an initialization function) if models are large and reused across jobs.
- **`requirements.txt`:** Add any Python libraries your worker needs to this file. These will be installed via `uv` when the Docker image is built.
- **`Dockerfile`:**
  - This file defines the Docker image for your worker.
  - It starts from a [RunPod base image (`runpod/base`)](https://github.com/runpod/containers/tree/main/official-templates/base) which includes CUDA, mulitple versions of python, uv, jupyter notebook and common dependencies.
  - It installs dependencies from `requirements.txt` using `uv`.
  - It copies your `src` directory into the image.
  - You might need to add system dependencies (`apt-get install ...`), environment variables (`ENV`), or other setup steps here if required by your specific application.
- **`test_input.json`:** Modify this file to provide relevant sample input for local testing.

## Testing Locally

You can test your handler logic locally using the RunPod Python SDK. For detailed steps on setting up your local environment (creating a virtual environment, installing dependencies) and running the handler, please refer to the [RunPod Serverless Get Started Guide](https://docs.runpod.io/serverless/get-started).

1.  **Prepare Input:** Modify `test_input.json` with relevant sample input for your handler.
2.  **Run the Handler:**
    ```bash
    python handler.py
    ```
    This will execute your `handler` function with the contents of [`test_input.json`](/test_input.json) as input.

## Deploying to RunPod

There are two main ways to deploy your worker:

1.  **GitHub Integration (Recommended):**

    - Connect your GitHub repository to RunPod Serverless. RunPod will automatically build and deploy your worker whenever you push changes to your specified branch.
    - For detailed instructions on setting up the GitHub integration, authorizing RunPod, and configuring your deployment, please refer to the [RunPod Deploy with GitHub Guide](https://docs.runpod.io/serverless/github-integration).

2.  **Manual Docker Build & Push:**
    - For detailed instructions on building the Docker image locally and pushing it to a container registry, please see the [RunPod Serverless Get Started Guide](https://docs.runpod.io/serverless/get-started#step-6-build-and-push-your-docker-image).
    - Once pushed, create a new Template or Endpoint in the RunPod Serverless UI and point it to the image in your container registry.

## Further Information

- [RunPod Serverless Documentation](https://docs.runpod.io/serverless/overview)
- [Python SDK](https://github.com/runpod/runpod-python)
- [Base Docker Images](https://github.com/runpod/containers/tree/main/official-templates/base)
- [Community Discord](https://discord.gg/cUpRmau42Vd)
