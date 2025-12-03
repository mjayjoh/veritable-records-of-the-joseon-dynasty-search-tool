"""Configuration settings for the MCP server."""

import os
from pathlib import Path


class Settings:
    """Server configuration settings."""

    # Application settings
    app_name: str = "text-analysis-mcp"
    app_instructions: str = "Text analysis and document search MCP server"

    # Server settings
    host: str = "0.0.0.0"
    port: int = int(os.environ.get("PORT", "8000"))

    # Corpus settings
    corpus_dir: str = "data/corpus"

    # TF-IDF settings
    tfidf_max_df: float = 0.85
    tfidf_min_df: int = 1
    tfidf_ngram_range: tuple[int, int] = (1, 2)

    # Answer synthesis settings
    top_sources_count: int = 3
    max_answer_words: int = 120
    max_snippet_words: int = 50

    # Logging settings
    log_level: str = "INFO"

    def get_corpus_path(self) -> Path:
        """Get the absolute path to the corpus directory."""
        # Try to get from environment variable first
        data_dir = os.environ.get("DATA_DIR")
        if data_dir:
            return Path(data_dir) / "corpus"

        # Fall back to project-relative path
        return Path(self.corpus_dir)


# Global configuration instance
config = Settings()
