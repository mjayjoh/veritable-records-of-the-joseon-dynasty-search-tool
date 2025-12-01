# Default target
.DEFAULT_GOAL := help

# Project variables
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
project_name := "silloc-search-tool"
project_dir := "$(patsubst %/,%,$(dir $(mkfile_path)))"

# Optional: Mount a data directory if DATA_DIR is set
mount_data := $(if $(DATA_DIR),-v $(DATA_DIR):/project/data,)

.PHONY: build run run-interactive test clean help

# Build Docker image
build: ## Build the Docker image
	docker compose build

# Run the server in the container
run: build ## Run the MCP server
	docker compose run --rm --service-ports $(mount_data) $(project_name) uv run python src/server.py --http

# Run interactive bash session in container
run-interactive: build ## Run an interactive bash session in the container
	docker compose run --rm --service-ports $(mount_data) $(project_name) /bin/bash

# Run tests (placeholder, no tests yet)
test: build ## Run pytest tests
	docker compose run --rm $(mount_data) $(project_name) uv run python -m pytest -v

# Clean up Docker images and containers
clean: ## Clean up all Docker images, containers, and volumes
	docker compose down --rmi all --volumes --remove-orphans
	docker image prune -f

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@echo "  build            Build the Docker image"
	@echo "  run              Run the MCP server in HTTP mode"
	@echo "  run-interactive  Run an interactive bash session in the container"
	@echo "  test             Run pytest tests"
	@echo "  clean            Clean up all Docker resources"
	@echo "  help             Show this help message"
	@echo ""
	@echo "Quick start:"
	@echo "  1. make build"
	@echo "  2. make run"
	@echo ""
	@echo "To get a shell inside the container:"
	@echo "  make run-interactive"
	@echo ""
