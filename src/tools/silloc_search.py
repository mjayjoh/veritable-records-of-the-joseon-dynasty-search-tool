"""Tool for searching the Korean Classics DB (db.itkc.or.kr).

This module is focused on searching the Annals of the Joseon Dynasty (조선왕조실록).

Best practices:
    1. Start with `search_joseon_annals` (or the advanced variant) to gather
       candidate documents, then request full text via `fetch_joseon_annal_texts`
       using the returned `document_id`.
    2. Paginate by increasing `start` in multiples of `rows`; rely on
       `total_results` to know when you’ve reached the end.
    3. Use `king_name` preferentially; fall back to `bibliography_id` if the name
       isn’t in `SILLOK_ID_MAP`.
    4. Reach for `search_joseon_annals_advanced` when you need title-only search,
       extended matching, or explicit ID filtering.
    5. Expect the detail payload to include only `text_url`/`image_url`; the raw
       browser URL has been intentionally omitted.
"""

import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from requests import Request

from schemas import (
    ClassicDocument,
    ClassicDocumentDetail,
    ClassicSearchResponse,
)

logger = logging.getLogger(__name__)


# Regex to strip HTML tags
CLEAN_HTML_RE = re.compile("<.*?>")
BASE_URL = "http://db.itkc.or.kr/openapi/search"
NODE_BASE_URL = "https://db.itkc.or.kr/dir/node"
OUTLINK_BASE_URL = "https://db.itkc.or.kr/dir/outLink"
PRINT_BASE_URL = "https://db.itkc.or.kr/popup/print.do"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    )
}

SILLOK_ID_MAP = {
    # Hangeul
    "태조": "ITKC_JT_A0",
    "정종": "ITKC_JT_B0",
    "태종": "ITKC_JT_C0",
    "세종": "ITKC_JT_D0",
    "문종": "ITKC_JT_E0",
    "단종": "ITKC_JT_F0",
    "세조": "ITKC_JT_G0",
    "예종": "ITKC_JT_H0",
    "성종": "ITKC_JT_I0",
    "연산군": "ITKC_JT_J0",
    "중종": "ITKC_JT_K0",
    "인종": "ITKC_JT_L0",
    "명종": "ITKC_JT_M0",
    "선조": "ITKC_JT_N0",
    "선조(수정)": "ITKC_JT_N1",
    "광해군": "ITKC_JT_O0",
    "인조": "ITKC_JT_P0",
    "효종": "ITKC_JT_Q0",
    "현종": "ITKC_JT_R0",
    "현종(개수)": "ITKC_JT_R1",
    "숙종": "ITKC_JT_S0",
    "숙종보궐정오": "ITKC_JT_S1",
    "경종": "ITKC_JT_T0",
    "경종(수정)": "ITKC_JT_T1",
    "영조": "ITKC_JT_U0",
    "정조": "ITKC_JT_V0",
    "순조": "ITKC_JT_W0",
    "헌종": "ITKC_JT_X0",
    "철종": "ITKC_JT_Y0",
    # Romanized
    "taejo": "ITKC_JT_A0",
    "jeongjong": "ITKC_JT_B0",
    "taejong": "ITKC_JT_C0",
    "sejong": "ITKC_JT_D0",
    "munjong": "ITKC_JT_E0",
    "danjong": "ITKC_JT_F0",
    "sejo": "ITKC_JT_G0",
    "yejong": "ITKC_JT_H0",
    "seongjong": "ITKC_JT_I0",
    "yeonsangun": "ITKC_JT_J0",
    "jungjong": "ITKC_JT_K0",
    "injong": "ITKC_JT_L0",
    "myeongjong": "ITKC_JT_M0",
    "seonjo": "ITKC_JT_N0",
    "seonjo(revised)": "ITKC_JT_N1",
    "gwanghaegun": "ITKC_JT_O0",
    "injo": "ITKC_JT_P0",
    "hyojong": "ITKC_JT_Q0",
    "hyeonjong": "ITKC_JT_R0",
    "hyeonjong(revised)": "ITKC_JT_R1",
    "sukjong": "ITKC_JT_S0",
    "sukjong(supplement)": "ITKC_JT_S1",
    "gyeongjong": "ITKC_JT_T0",
    "gyeongjong(revised)": "ITKC_JT_T1",
    "yeongjo": "ITKC_JT_U0",
    "jeongjo": "ITKC_JT_V0",
    "sunjo": "ITKC_JT_W0",
    "heonjong": "ITKC_JT_X0",
    "cheoljong": "ITKC_JT_Y0",
}


def _perform_search(params: dict) -> ClassicSearchResponse:
    """Internal function to perform the search and parse XML."""
    doc_list = []
    total_count = 0

    # Handle 'q' parameter specially - it should have literal † and $ separators
    # Extract 'q' if present, and construct URL manually to avoid double-encoding
    q_value = params.pop("q", None)

    if q_value:
        # Build URL with q parameter having literal separators
        # The q_value format is: query†{query}$opDir†{bib_id}
        # We need to URL-encode the query part but keep separators literal
        # Split q_value, encode the query part, then reassemble
        from urllib.parse import urlencode

        # Parse the q_value to extract parts
        # Format: query†{query}$opDir†{bib_id}
        if "†" in q_value and "$" in q_value:
            parts = q_value.split("$")
            encoded_parts = []
            for part in parts:
                if "†" in part:
                    # Split by † to get the key and value
                    key, value = part.split("†", 1)
                    if key == "query":
                        # URL-encode only the query value
                        from urllib.parse import quote

                        encoded_value = quote(value, safe="")
                        encoded_parts.append(f"{key}†{encoded_value}")
                    else:
                        # opDir value (bib_id) doesn't need encoding
                        encoded_parts.append(part)
                else:
                    encoded_parts.append(part)
            encoded_q = "$".join(encoded_parts)
        else:
            # Fallback: encode the whole thing
            from urllib.parse import quote

            encoded_q = quote(q_value, safe="†$")

        other_params = urlencode(params)
        url = f"{BASE_URL}?{other_params}&q={encoded_q}"
        logger.info("Search URL with q parameter: %s", url)
        response = requests.get(url, timeout=10)
    else:
        # Normal case: use params dict (requests will encode everything)
        request = Request("GET", BASE_URL, params=params).prepare()
        logger.info("Search URL with keyword: %s", request.url)
        response = requests.get(BASE_URL, params=params, timeout=10)

    response.raise_for_status()
    # We use response.content to handle encoding correctly
    root = ET.fromstring(response.content)
    # Extract totalCount from header using XPath
    total_count_elem = root.find("./header/field[@name='totalCount']")
    if total_count_elem is not None and total_count_elem.text:
        total_count = int(total_count_elem.text)
        logger.info("API returned totalCount: %d", total_count)
        # Also log the keyword from response to see what the API received
        keyword_elem = root.find("./header/field[@name='keyword']")
        if keyword_elem is not None and keyword_elem.text:
            logger.info("API response keyword: %s", keyword_elem.text)
    else:
        logger.warning(
            "API response missing totalCount field. Response content: %s",
            response.content[:500],
        )

    if total_count == 0:
        return ClassicSearchResponse(total_results=0, documents=[])

    # Find all document records
    doc_elements = root.findall(".//doc")
    for doc in doc_elements:
        fields_dict = {}
        field_elements = doc.findall("field")

        for field in field_elements:
            name = field.get("name")
            value = field.text
            if name and value:
                fields_dict[name] = value

        if fields_dict:
            clean_snippet = fields_dict.get("검색필드", "")
            if clean_snippet:
                clean_snippet = CLEAN_HTML_RE.sub("", clean_snippet)

            mapped_data = {
                "title": fields_dict.get("서명"),
                "article_title": fields_dict.get("기사명"),
                "author": fields_dict.get("저자"),
                "reign_year": fields_dict.get("편년연호"),
                "year_gregorian": fields_dict.get("편년서기년"),
                "month": fields_dict.get("편년월"),
                "day": fields_dict.get("편년일"),
                "snippet": clean_snippet,
                "bibliography_id": fields_dict.get("서지ID"),
                "document_id": fields_dict.get("자료ID"),
                "dci_s": fields_dict.get("DCI_s"),
                "item_id": fields_dict.get("아이템ID"),
                "subject_classification": fields_dict.get("주제분류"),
                "library_classification": fields_dict.get("사부분류"),
            }
            doc_list.append(ClassicDocument(**mapped_data))

    return ClassicSearchResponse(total_results=total_count, documents=doc_list)


def _build_url(base_url: str, params: dict[str, str]) -> str:
    """Create a fully encoded URL for logging and responses."""
    request = Request("GET", base_url, params=params).prepare()
    return request.url


def _extract_paragraphs(container_selector: str, soup: BeautifulSoup) -> list[str]:
    """Pull paragraph text from the specified container."""
    paragraphs = []
    for node in soup.select(f"{container_selector} p.paragraph"):
        text = node.get_text(separator=" ", strip=True)
        if text:
            paragraphs.append(text)
    return paragraphs


def _fetch_print_paragraphs(article_code: str, gubun: str) -> list[str]:
    """Fallback helper to pull paragraphs from the print view."""
    response = requests.get(
        PRINT_BASE_URL,
        params={"id": article_code, "gubun": gubun},
        headers=DEFAULT_HEADERS,
        timeout=10,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    container = None
    for selector in (
        "div.view_txt",
        "div.view_con",
        "div.view_area",
        "div#printArea",
    ):
        container = soup.select_one(selector)
        if container:
            break

    if not container:
        text = soup.get_text("\n", strip=True)
        return [line for line in text.splitlines() if line.strip()]

    paragraphs = [node.get_text(" ", strip=True) for node in container.select("p")]
    if not paragraphs:
        text = container.get_text("\n", strip=True)
        return [line for line in text.splitlines() if line.strip()]

    return [paragraph for paragraph in paragraphs if paragraph]


def _fetch_text_outlink(
    document_id: str,
) -> tuple[list[str], list[str], str | None, str | None]:
    """Fallback helper that scrapes the TXT outlink page."""
    response = requests.get(
        OUTLINK_BASE_URL,
        params={"linkType": "txt", "dataId": document_id},
        headers=DEFAULT_HEADERS,
        timeout=10,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    heading_node = soup.select_one("div.list_tit2 h3")
    heading = heading_node.get_text(" ", strip=True) if heading_node else None

    article_title_node = soup.select_one("div.text_body_tit h4")
    article_title = (
        article_title_node.get_text(" ", strip=True) if article_title_node else None
    )

    translation = _extract_paragraphs("div.ins_view_left", soup)
    original = _extract_paragraphs("div.ins_view_right", soup)

    return translation, original, heading, article_title


def search_joseon_annals(
    query: str,
    search_field: str = "all",
    king_name: str | None = None,
    bibliography_id: str | None = None,
    start: int = 0,
    rows: int = 20,
) -> ClassicSearchResponse:
    """Performs a classic search on the Silloc API.

    Args:
        query (str): The search term (keyword), expected to be in Korean.
        search_field (str): The area of the annals to search.
            Valid options are: 'all' (default), 'body', 'article_title'.
            Maps to `JT_AA`, `JT_BD`, `JT_GS` respectively.
        king_name (str | None): The human-readable name of the king
            (e.g., 'Sejong', '태종'). This is translated via
            `SILLOK_ID_MAP` to a bibliography ID.
        bibliography_id (str | None): The specific bibliography ID to search
            (e.g., 'ITKC_JT_C0'). This is used as a fallback
            if `king_name` is not provided or not found.
        start (int): The result offset for pagination (API 'start' param).
        rows (int): The number of results to return (API 'rows' param).

    Returns:
        ClassicSearchResponse: A Pydantic object containing the
            `total_results` and a list of `ClassicDocument` objects.
            Returns an empty response in case of an HTTP or XML error.
    """
    sec_id_map = {"all": "JT_AA", "body": "JT_BD", "article_title": "JT_GS"}
    secId = sec_id_map.get(search_field, "JT_AA")

    params = {"secId": secId, "start": start, "rows": rows}

    bib_id = None
    if king_name:
        normalized_name = king_name.lower().strip()
        bib_id = SILLOK_ID_MAP.get(normalized_name)
        if not bib_id:
            # Log warning if king name not found in map
            logger.warning(
                "King name '%s' (normalized: '%s') not found in SILLOK_ID_MAP. "
                "Available keys: %s",
                king_name,
                normalized_name,
                list(SILLOK_ID_MAP.keys())[:10],  # Show first 10 keys
            )
        else:
            logger.info(
                "Mapped king_name '%s' to bibliography_id '%s'", king_name, bib_id
            )

    if not bib_id and bibliography_id:
        bib_id = bibliography_id

    if bib_id:
        # Construct q parameter with literal separators
        # Format: query†{query}$opDir†{bibliography_id}
        # Note: We use raw query here - the URL encoding will happen when building the full URL
        # The separators † and $ should remain literal in the final URL
        q_parts = [f"query†{query}", f"opDir†{bib_id}"]
        params["q"] = "$".join(q_parts)
        # Log the constructed q parameter for debugging
        logger.info("Using q parameter with opDir: %s", params["q"])
    else:
        params["keyword"] = query
        logger.info("Using keyword parameter: %s", query)

    return _perform_search(params)


def fetch_joseon_annal_texts(document_id: str) -> ClassicDocumentDetail:
    """Fetch both translation and original text columns for a given annals article.

    Args:
        document_id: 자료ID for the desired article (e.g., 'ITKC_JT_A0_A04_07A_01A_00010')

    Returns:
        ClassicDocumentDetail payload containing both language columns and helpful URLs.
        If a network or parsing error occurs, the text fields are returned empty while
        still providing the constructed URLs for downstream handling
    """
    if not document_id:
        raise ValueError("document_id must be provided.")

    normalized_document_id = document_id.strip()

    node_params = {
        "itemId": "JT",
        "gubun": "book",
        "dataGubun": "최종정보",
        "dataId": normalized_document_id,
    }
    text_url = _build_url(
        OUTLINK_BASE_URL, {"linkType": "txt", "dataId": normalized_document_id}
    )
    image_url = _build_url(
        OUTLINK_BASE_URL, {"linkType": "img", "dataId": normalized_document_id}
    )

    response = requests.get(
        NODE_BASE_URL,
        params=node_params,
        headers=DEFAULT_HEADERS
        | {"Referer": "https://db.itkc.or.kr/dir/item?itemId=JT"},
        timeout=10,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    heading_node = soup.select_one("div.list_tit2 h3")
    heading = heading_node.get_text(separator=" ", strip=True) if heading_node else None

    article_title_node = soup.select_one("div.text_body_tit h4")
    article_title = (
        article_title_node.get_text(separator=" ", strip=True)
        if article_title_node
        else None
    )

    translation = _extract_paragraphs("div.ins_view_left", soup)
    original = _extract_paragraphs("div.ins_view_right", soup)

    dci_button = soup.select_one("a[data-dci-copy]")
    dci_value = dci_button.get("data-dci-copy") if dci_button else None

    if (not translation or not original) and soup:
        match = re.search(r"popPrint\('([^']+)'", response.text)
        article_code = match.group(1) if match else None
        if article_code:
            if not translation:
                translation = _fetch_print_paragraphs(article_code, "kor")
            if not original:
                original = _fetch_print_paragraphs(article_code, "chn")

    if not translation or not original or not heading or not article_title:
        txt_translation, txt_original, txt_heading, txt_title = _fetch_text_outlink(
            normalized_document_id
        )
        if not translation:
            translation = txt_translation
        if not original:
            original = txt_original
        if not heading and txt_heading:
            heading = txt_heading
        if not article_title and txt_title:
            article_title = txt_title

    return ClassicDocumentDetail(
        document_id=normalized_document_id,
        article_title=article_title,
        heading=heading,
        translation_paragraphs=translation,
        original_paragraphs=original,
        dci=dci_value,
        text_url=text_url,
        image_url=image_url,
    )


def search_joseon_annals_advanced(
    query: str,
    search_field: str = "all",
    king_names: list[str] | None = None,
    bibliography_ids: list[str] | None = None,
    extended_search: bool = False,
    start: int = 0,
    rows: int = 20,
) -> ClassicSearchResponse:
    """Advanced search for the Annals of the Joseon Dynasty (조선왕조실록).

    This function provides additional search capabilities beyond the basic search,
    including searching across multiple kings, extended search mode, and title search.

    Args:
        query (str): The search term (keyword), expected to be in Korean.
        search_field (str): The area of the annals to search.
            Valid options: 'all' (default), 'title' (서지), 'body', 'article_title'.
            Maps to `JT_AA`, `JT_SJ`, `JT_BD`, `JT_GS` respectively.
        king_names (list[str] | None): List of human-readable king names to search.
            e.g., ['Sejong', '태종', 'Seonjo']. This is translated via `SILLOK_ID_MAP`
            to bibliography IDs. Note: The API opDir parameter accepts a single ID,
            so if multiple kings are provided, the first valid one is used for filtering.
        bibliography_ids (list[str] | None): List of specific bibliography IDs to search.
            e.g., ['ITKC_JT_C0', 'ITKC_JT_D0']. Note: The API opDir parameter accepts
            a single ID, so if multiple IDs are provided, the first one is used.
            If both king_names and bibliography_ids are provided, king_names take precedence.
        extended_search (bool): If True, uses extended search mode (opExt=Y) for more
            flexible matching. If False (default), uses basic search mode (opExt=N).
        start (int): The result offset for pagination (API 'start' param).
        rows (int): The number of results to return (API 'rows' param).

    Returns:
        ClassicSearchResponse: A Pydantic object containing the
            `total_results` and a list of `ClassicDocument` objects.
            Returns an empty response in case of an HTTP or XML error.
    """
    sec_id_map = {
        "all": "JT_AA",
        "title": "JT_SJ",
        "body": "JT_BD",
        "article_title": "JT_GS",
    }
    secId = sec_id_map.get(search_field, "JT_AA")

    params = {"secId": secId, "start": start, "rows": rows}

    # Build query parameter with advanced options
    # URL-encode only the query string, keep separators († and $) as literals
    # Format: query†{encoded_query}$opDir†{bibliography_id}$opExt†{Y|N}
    encoded_query = quote(query)
    q_parts = [f"query†{encoded_query}"]

    # Collect all bibliography IDs from both king_names and bibliography_ids
    all_bib_ids = []

    if king_names:
        for king_name in king_names:
            normalized_name = king_name.lower().strip()
            bib_id = SILLOK_ID_MAP.get(normalized_name)
            if bib_id and bib_id not in all_bib_ids:
                all_bib_ids.append(bib_id)

    if bibliography_ids:
        for bib_id in bibliography_ids:
            if bib_id and bib_id not in all_bib_ids:
                all_bib_ids.append(bib_id)

    # If we have bibliography IDs, use opDir
    # The API may support multiple IDs separated by ^ (like opJib), but for opDir
    # we'll use the first one. If multiple kings are needed, consider making
    # separate calls or using a union approach
    if all_bib_ids:
        # Use the first bibliography ID for opDir
        # Note: The API opDir parameter typically accepts a single ID
        # For searching multiple kings, you may need to make separate calls
        q_parts.append(f"opDir†{all_bib_ids[0]}")

    # Add extended search option only if explicitly requested
    # According to API docs, opExt is optional; only include when needed
    if extended_search:
        q_parts.append("opExt†Y")

    # Use 'q' parameter for advanced search (when we have opDir or opExt)
    # Otherwise, fall back to simple 'keyword' parameter
    if len(q_parts) > 1:  # More than just the query part
        # The q parameter will be handled specially in _perform_search to preserve
        # the literal † and $ separators as required by the API
        params["q"] = "$".join(q_parts)
    else:
        # Simple search without advanced options - use keyword parameter
        params["keyword"] = query

    return _perform_search(params)
