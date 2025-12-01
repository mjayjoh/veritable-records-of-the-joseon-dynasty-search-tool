"""Pydantic schemas for MCP server tools.

This module defines the data models for tool inputs and outputs.
"""

from pydantic import BaseModel, Field

class ClassicDocument(BaseModel):
    """Represents a single document from the Korean Classics database"""

    # Title and author fields
    title: str | None = Field(default=None, description="서명: The title of the book.")
    article_title: str | None = Field(
        default=None, description="기사명: The title of the specific article."
    )
    author: str | None = Field(default=None, description="저자: The author(s).")

    # Date fields
    reign_year: str | None = Field(
        default=None, description="편년연호: Reign-period year name."
    )
    year_gregorian: str | None = Field(
        default=None, description="편년서기년: Gregorian year."
    )
    month: str | None = Field(default=None, description="편년월: Month.")
    day: str | None = Field(default=None, description="편년일: Day.")

    # Content
    snippet: str | None = Field(
        default=None, description="검색필드: A snippet of the body text."
    )

    # Classification & IDs
    bibliography_id: str | None = Field(
        default=None, description="서지ID: The bibliographic ID."
    )
    document_id: str | None = Field(
        default=None, description="자료ID: The specific document ID."
    )
    dci_s: str | None = Field(
        default=None, description="DCI_s: DCI (Digital Content Identifier)."
    )
    item_id: str | None = Field(
        default=None, description="아이템ID: Item ID (e.g., ITKC_JT)."
    )
    subject_classification: str | None = Field(
        default=None, description="주제분류: Subject classification."
    )
    library_classification: str | None = Field(
        default=None, description="사부분류: Library classification."
    )


class ClassicDocumentDetail(BaseModel):
    """Full text payload for a single Joseon annals article."""

    document_id: str = Field(
        ..., description="자료ID: Unique identifier for the annals article."
    )
    article_title: str | None = Field(
        default=None, description="기사명: Human-readable article title."
    )
    heading: str | None = Field(
        default=None,
        description="Combined heading information (e.g., reign year/date) shown on the page.",
    )
    translation_paragraphs: list[str] = Field(
        default_factory=list,
        description="Modern Korean translation paragraphs captured from the left column.",
    )
    original_paragraphs: list[str] = Field(
        default_factory=list,
        description="Classical Chinese/Hanja paragraphs captured from the right column.",
    )
    dci: str | None = Field(
        default=None, description="Digital Content Identifier copied from the page."
    )
    text_url: str = Field(
        ..., description="Direct TXT endpoint exposed by the '원문' button."
    )
    image_url: str | None = Field(
        default=None, description="Direct image viewer endpoint (if available)."
    )


class ClassicSearchResponse(BaseModel):
    """The complete response for a Korean Classics search."""

    total_results: int = Field(
        ..., description="Total number of matching results found."
    )
    documents: list[ClassicDocument] = Field(
        ..., description="A list of documents for the current page."
    )
