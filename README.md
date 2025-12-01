# Veritable Records of the Joseon Dynasty Search Tool

## Project Background

This project provides a Model Context Protocol (MCP) server for searching the [Veritable Records of the Joseon Dynasty (조선왕조실록)](https://sillok.history.go.kr/), one of the most important historical documents of Korea. It acts as a wrapper around the [Korean Classics DB (db.itkc.or.kr)](http://db.itkc.or.kr/), making this invaluable resource accessible to modern AI assistants and other programmatic tools.

Researchers, historians, and enthusiasts can use this server to perform queries, retrieve full-text articles, and integrate the annals' data into their own workflows without needing to scrape the website directly.

## Tools:
- `search_joseon_annals_tool`: Search for articles by keyword, with filters for specific kings.
- `fetch_joseon_annals_article_tool`: Retrieve the full text of an article, including the modern Korean translation and the original Classical Chinese (Hanja) text.

## Project Structure

```
.
├── src/
│   ├── config/
│   │   └── settings.py      # Configuration settings
│   ├── schemas.py           # Pydantic data models
│   ├── server.py            # Main FastMCP server
│   └── tools/
│       └── silloc_search.py # Core search and fetch logic
├── docker-compose.yaml      # Docker Compose configuration
├── Dockerfile               # Docker container definition
├── Makefile                 # Make commands for development
├── pyproject.toml           # Python dependencies
└── README.md
```

## Tools

### 1. `search_joseon_annals_tool`
This tool allows you to search for articles within the annals.

-   **Functionality**: Searches by a Korean keyword. You can optionally filter the search to the annals of a specific king.
-   **Input**: `query` (str), `search_field` (str, optional), `king_name` (str, optional), `start` (int, optional), `rows` (int, optional).
-   **Output**: A list of `ClassicDocument` objects, including titles, snippets, and most importantly, the `document_id` for each article.

### 2. `fetch_joseon_annals_article_tool`
Once you have a `document_id` from the search tool, you can use this tool to get the full content.

-   **Functionality**: Retrieves the complete text of a single article.
-   **Input**: `document_id` (str).
-   **Output**: A `ClassicDocumentDetail` object containing:
    -   `translation_paragraphs`: A list of paragraphs in modern Korean.
    -   `original_paragraphs`: A list of paragraphs in the original Classical Chinese.
    -   `text_url` and `image_url`: Direct links to the article on the source website.

### Example Workflow
1.  Call `search_joseon_annals_tool` with a query like `"정도전"`.
2.  From the results, pick a document and get its `document_id`.
3.  Call `fetch_joseon_annals_article_tool` with that `document_id` to read the full article.

## Getting Started

### Prerequisites
-   **Docker**: [An introduction to Docker](https://docker-curriculum.com/)
-   **Make**: Should be pre-installed on macOS/Linux.

### Running the Server
All commands are run from your host machine's terminal.

1.  **Build the Docker image**
    ```bash
    make build
    ```

2.  **Run the server**
    The server will start in HTTP mode on `http://localhost:8000`.
    ```bash
    make run
    ```

    Alternatively, to get an interactive shell inside the running container:
    ```bash
    make run-interactive
    ```

## Usage & Testing

### Running Tests
Currently, there are no automated tests for this project.

### Docker & Make
We use `docker` and `make` to streamline development. Common `make` commands:

*   `make build`: Build the Docker image.
*   `make run`: Start the MCP server in HTTP mode.
*   `make run-interactive`: Start an interactive bash session in the container.
*   `make clean`: Clean up Docker images and containers.

The `Makefile` contains the details for each command.

## Technical Details

### Environment
Development is done entirely within a Docker container to ensure consistency.

### Package Management
We use [uv](https://docs.astral.sh/uv/) for Python environment and package management _inside the container_. Key dependencies are defined in `pyproject.toml`:
- `fastmcp`
- `pydantic`
- `beautifulsoup4`
- `requests`

### Style
We use [`ruff`](https://docs.astral.sh/ruff/) to enforce style standards.
