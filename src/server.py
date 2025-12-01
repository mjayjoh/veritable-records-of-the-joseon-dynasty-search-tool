"""MCP server for searching the Annals of the Joseon Dynasty (조선왕조실록).

This server provides tools for searching the Korean Classics DB specifically
focused on the Annals of the Joseon Dynasty.
"""

import logging
import sys

from fastmcp import FastMCP

from config.settings import config
from schemas import ClassicDocumentDetail, ClassicSearchResponse
from tools.silloc_search import (
    fetch_joseon_annal_texts,
    search_joseon_annals,
)

# Set up logging
# For STDIO mode, logging goes to stderr to avoid interfering with MCP protocol on stdout
logging.basicConfig(
    level=getattr(logging, config.log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Use stderr for STDIO compatibility
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP(
    name="joseon-annals-mcp",
    instructions="MCP server for searching the Annals of the Joseon Dynasty (조선왕조실록) from the Korean Classics DB",
)


@mcp.tool
def search_joseon_annals_tool(
    query: str,
    search_field: str = "all",
    king_name: str | None = None,
    start: int = 0,
    rows: int = 20,
) -> ClassicSearchResponse:
    """Searches the Annals of the Joseon Dynasty with simple query (조선왕조실록).

    To retrieve the full original text and image for a search result:
        1. Extract the `document_id` field from any document in the response's `documents` list
        2. Call `fetch_joseon_annals_article_tool` with that `document_id` to get:
           - `translation_paragraphs`: Modern Korean translation
           - `original_paragraphs`: Classical Chinese/Hanja original text
           - `text_url`: Direct URL to the text view
           - `image_url`: Direct URL to the image view

    Example workflow:
        response = search_joseon_annals_tool(query="정도전")
        document_id = response.documents[0].document_id
        detail = fetch_joseon_annals_article_tool(document_id)
        # Now access detail.original_paragraphs, detail.image_url, etc.

    Args:
        query: The search term, which should be in Korean (e.g., '정도전', '왜란').
        search_field: Area to search.
                      Options: 'all' (default), 'body', 'article_title'.
        king_name: Filter to a specific king's annal.
                   e.g., 'Taejo', '세종', 'Seonjo', '선조'.
        start: Result offset for pagination (0-indexed). Use this to paginate through results.
               For example: start=0 returns the first page, start=20 returns results 21-40,
               start=40 returns results 41-60, etc. The response includes 'total_results'
               which indicates the total number of results available. To get the next page,
               increment 'start' by the 'rows' value (e.g., if rows=20, use start=20, 40, 60...).
        rows: Number of results to return per page (default 20). Maximum recommended: 100.

    Returns:
        ClassicSearchResponse: Contains 'total_results' (total count) and 'documents'
        (list of results for the current page). Use 'total_results' and 'rows' to calculate
        total pages: total_pages = ceil(total_results / rows). To get more results, call
        again with start = previous_start + rows.
    """
    valid_fields = ["all", "body", "article_title"]
    if search_field not in valid_fields:
        search_field = "all"

    logger.info(
        "Search request: query='%s', search_field='%s', king_name='%s', "
        "start=%d, rows=%d",
        query,
        search_field,
        king_name,
        start,
        rows,
    )

    result = search_joseon_annals(
        query,
        search_field=search_field,
        king_name=king_name,
        start=start,
        rows=rows,
    )

    logger.info(
        "Search completed: found %d total results, returning %d documents",
        result.total_results,
        len(result.documents),
    )

    return result


@mcp.tool
def fetch_joseon_annals_article_tool(document_id: str) -> ClassicDocumentDetail:
    """Retrieve both translation and original text for a specific annals article.

    Args:
        document_id: 자료ID for the article (e.g., 'ITKC_JT_A0_A04_07A_01A_00010').

    Returns:
        ClassicDocumentDetail: Full text payload including translation/original columns
        and convenience URLs for the browser, text, and image views.
    """
    logger.info("Fetching article detail for document_id='%s'", document_id)
    result = fetch_joseon_annal_texts(document_id)
    logger.info(
        "Fetched article detail for document_id='%s' (translation paragraphs=%d, original paragraphs=%d)",
        document_id,
        len(result.translation_paragraphs),
        len(result.original_paragraphs),
    )
    return result


if __name__ == "__main__":
    # Run the server
    # For testing with MCP Inspector, use stdio transport (default)
    # For production deployment, you can use: transport="http"
    import sys

    logger.info("Starting joseon-annals-mcp server...")

    if "--http" in sys.argv:
        # HTTP transport for production
        logger.info("Running in HTTP mode on %s:%d", config.host, config.port)
        mcp.run(transport="http", host=config.host, port=config.port)
    else:
        # STDIO transport for testing with MCP Inspector (default)
        logger.info("Running in STDIO mode")
        mcp.run(transport="stdio")
