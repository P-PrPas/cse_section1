"""
Document retrieval module.
Fetches digital original exam documents via HTTP and decodes them
as in-memory images (no disk writes for performance and privacy).

Supports both direct image URLs and PDF links — PDFs are rendered
from their first page using PyMuPDF.
"""

import re
import logging

import cv2
import fitz  # PyMuPDF
import numpy as np
import requests
import time

logger = logging.getLogger(__name__)

# PDF DPI for first-page rendering (higher = better quality, slower)
_PDF_RENDER_DPI = 200

_FETCH_CACHE = {}  # url: (image_array, timestamp)
_CACHE_TTL = 3600  # 1 hour validation


class InvalidURLError(Exception):
    """Raised when the scanned QR data is not a valid URL."""
    pass


class FetchTimeoutError(Exception):
    """Raised when the HTTP request exceeds the timeout."""
    pass


class ImageDecodeError(Exception):
    """Raised when the downloaded data cannot be decoded as an image."""
    pass


class PDFRenderError(Exception):
    """Raised when a PDF cannot be rendered to an image."""
    pass


def validate_url(url: str, pattern: str = r"^https?://.+") -> bool:
    """
    Validate that the given string matches the expected URL pattern.

    Args:
        url: The string to validate.
        pattern: Regex pattern for valid URLs.

    Returns:
        True if the URL matches the pattern.
    """
    return bool(re.match(pattern, url.strip()))


def _transform_url(url: str) -> str:
    """Transform known viewing URLs into direct download URLs.
    
    Handles Google Drive:
    - https://drive.google.com/file/d/FILE_ID/view -> uc?export=download&id=FILE_ID
    - https://drive.google.com/open?id=FILE_ID -> uc?export=download&id=FILE_ID
    
    Handles Dropbox:
    - https://www.dropbox.com/...?dl=0 -> ...?dl=1
    """
    # Google Drive File ID match
    match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
        
    # Google Drive Open ID match
    match = re.search(r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)', url)
    if match:
        return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
        
    # Dropbox dl=0 match
    if 'dropbox.com/' in url and url.endswith('dl=0'):
        return url[:-1] + '1'
        
    return url


def _is_pdf(content: bytes, content_type: str) -> bool:
    """Detect whether the downloaded content is a PDF."""
    if content_type and "application/pdf" in content_type.lower():
        return True
    # Fallback: check %PDF magic bytes
    return content[:5] == b"%PDF-"


def _render_pdf_first_page(data: bytes, dpi: int = _PDF_RENDER_DPI) -> np.ndarray:
    """
    Render the first page of a PDF (from raw bytes) as an OpenCV BGR image.

    Args:
        data: Raw PDF file bytes.
        dpi: Resolution for rendering.

    Returns:
        BGR image as numpy array.

    Raises:
        PDFRenderError: If the PDF has no pages or rendering fails.
    """
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise PDFRenderError(f"Failed to open PDF: {e}")

    if doc.page_count == 0:
        doc.close()
        raise PDFRenderError("PDF contains no pages.")

    page = doc[0]
    zoom = dpi / 72  # 72 is the default PDF DPI
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    # Convert PyMuPDF pixmap (RGB) → numpy → BGR for OpenCV
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3
    )
    bgr_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    doc.close()
    logger.info(
        "PDF first page rendered at %d DPI: %dx%d",
        dpi, bgr_image.shape[1], bgr_image.shape[0],
    )
    return bgr_image


def fetch_document(url: str, timeout: int = 5,
                   url_pattern: str = r"^https?://.+") -> np.ndarray:
    """
    Fetch a document image from a URL and return it as an OpenCV image.

    Supports both direct image URLs and PDF links.  The content is
    downloaded into memory (no disk I/O) and decoded directly.

    Args:
        url: The URL to fetch the document from (image or PDF).
        timeout: HTTP request timeout in seconds.
        url_pattern: Regex pattern to validate the URL before fetching.

    Returns:
        BGR image as numpy array.

    Raises:
        InvalidURLError: If the URL doesn't match the expected pattern.
        FetchTimeoutError: If the request times out.
        ImageDecodeError: If the response cannot be decoded as an image.
        PDFRenderError: If a PDF cannot be rendered to an image.
    """
    url = url.strip()

    if not validate_url(url, url_pattern):
        raise InvalidURLError(
            f"Invalid URL format: '{url}'. "
            "Expected a URL starting with http:// or https://"
        )
        
    url = _transform_url(url)

    now = time.time()
    if url in _FETCH_CACHE:
        cached_img, timestamp = _FETCH_CACHE[url]
        if now - timestamp < _CACHE_TTL:
            logger.info("Using cached document for: %s", url)
            return cached_img.copy()
        else:
            del _FETCH_CACHE[url]

    try:
        logger.info("Fetching document from: %s", url)
        response = requests.get(url, timeout=timeout, stream=False)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise FetchTimeoutError(
            f"Request timed out after {timeout} seconds. "
            "Please check the internet connection."
        )
    except requests.exceptions.ConnectionError:
        raise FetchTimeoutError(
            "Cannot connect to server. "
            "Please check the internet connection."
        )
    except requests.exceptions.HTTPError as e:
        raise ImageDecodeError(
            f"Server returned error: {e.response.status_code}. "
            "The document URL may be invalid."
        )
    except requests.exceptions.RequestException as e:
        raise FetchTimeoutError(f"Network error: {str(e)}")

    content = response.content
    content_type = response.headers.get("Content-Type", "")

    # ── Handle HTML Wrappers (e.g., me-qr.com) ──────────────────────
    if "text/html" in content_type.lower() and "me-qr.com" in url:
        html_text = content.decode("utf-8", errors="ignore")
        match = re.search(r'https?://[^\s\'"]+\.pdf[^\s\'"]*', html_text)
        if match:
            real_pdf_url = match.group(0)
            logger.info("Found real PDF link in me-qr.com wrapper: %s", real_pdf_url)
            # Fetch the actual PDF recursively
            img = fetch_document(real_pdf_url, timeout=timeout, url_pattern=url_pattern)
            _FETCH_CACHE[url] = (img.copy(), time.time())
            return img

    # ── PDF path ────────────────────────────────────────────────────
    if _is_pdf(content, content_type):
        logger.info("PDF detected (Content-Type: %s). Rendering first page...", content_type)
        img = _render_pdf_first_page(content)
        _FETCH_CACHE[url] = (img.copy(), time.time())
        return img

    # ── Image path (existing behaviour) ─────────────────────────────
    image_bytes = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

    if image is None:
        raise ImageDecodeError(
            "Downloaded file is not a valid image or PDF. "
            "The URL may not point to a document."
        )

    logger.info("Document fetched successfully: %dx%d", image.shape[1], image.shape[0])
    _FETCH_CACHE[url] = (image.copy(), time.time())
    return image
