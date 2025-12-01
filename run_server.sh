#!/bin/bash
# Wrapper script to run MCP mj_server for Inspector
# This runs on HOST but executes inside Docker

# Find running container - try multiple patterns
CONTAINER=$(docker ps --filter "name=2025-autumn-mcp" --format "{{.ID}}" | head -n 1)

if [ -z "$CONTAINER" ]; then
    echo "Error: No running 2025-autumn-mcp container found" >&2
    echo "Please run: make run-interactive" >&2
    echo "Available containers:" >&2
    docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Image}}" >&2
    exit 1
fi

# Execute mj_server in container with STDIO transport
# Set PYTHONPATH to ensure imports work
docker exec -i "$CONTAINER" bash -c "cd /project && PYTHONPATH=/project/src uv run python -m server"

