# This is a basic docker image for use in the clinic
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Switch to root to update and install tools
RUN apt-get update && apt-get install -y curl git

# Create working directory
WORKDIR /project

# Copy dependency files first for better caching
COPY pyproject.toml .

# Resolve and install Python packages from pyproject/uv.lock
RUN /usr/local/bin/uv venv
ENV VIRTUAL_ENV=/project/.venv
ENV PATH="/project/.venv/bin:$PATH"
ENV PYTHONPATH=/project/src
RUN uv sync

# Ensure PYTHONPATH persists in interactive shells
RUN echo 'export PYTHONPATH=/project/src' >> /root/.bashrc

CMD ["/bin/bash"]