#!/bin/bash
# Wrapper script to run the server for Inspector
# This runs on HOST but executes inside Docker

# The service name from docker-compose.yaml
SERVICE_NAME="silloc-search-tool"

# Find running container ID using docker-compose. Redirect stderr to /dev/null to hide "project name is not set" warnings.
CONTAINER=$(docker-compose ps -q "$SERVICE_NAME" 2>/dev/null | head -n 1)

# Fallback to searching by name if compose fails (e.g. not in a compose project directory)
if [ -z "$CONTAINER" ]; then
    # This will match containers where the name includes the service name.
    CONTAINER=$(docker ps --filter "name=${SERVICE_NAME}" --format "{{.ID}}" | head -n 1)
fi

if [ -z "$CONTAINER" ]; then
    echo "Error: No running '$SERVICE_NAME' container found." >&2
    echo "Hint: A container for this service may be running." 
    echo "Run 'make run-interactive' in a separate terminal to start one." >&2
    echo "Currently running containers:" >&2
    docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Image}}" >&2
    exit 1
fi

echo "Found container $CONTAINER. Executing command..." >&2

# Execute server in container with STDIO transport
# The working directory is /project (from Dockerfile).
# PYTHONPATH is set to /project/src (from Dockerfile and here for redundancy).
docker exec -i "$CONTAINER" bash -c "PYTHONPATH=/project/src uv run python -m server"