"""OCR fallback for image-only PDFs.

Supports multiple OCR backends via provider pattern:
- paddleocr: PaddleOCR PP-OCRv5 (best Japanese accuracy, recommended)
- pymupdf: PyMuPDF built-in OCR (requires Tesseract system install)

The provider is selected automatically based on available packages,
or can be overridden via EIDP_OCR_PROVIDER env var.

Design for portability:
- All OCR deps are optional (ocr extra in pyproject.toml)
- If no OCR is available, returns empty text with a warning
- Output is plain text per page, compatible with parse_pdf's text pipeline
"""

from pathlib import Path

import structlog

log = structlog.get_logger()

_VALID_PROVIDERS = ("paddleocr", "pymupdf")


def _check_ocr_availability() -> str:
    """Detect available OCR provider. Returns provider name or 'none'."""
    import os

    override = os.environ.get("EIDP_OCR_PROVIDER", "").lower()
    if override in _VALID_PROVIDERS:
        return override

    # Auto-detect: prefer PaddleOCR > PyMuPDF OCR
    try:
        from paddleocr import PaddleOCR  # noqa: F401
        return "paddleocr"
    except ImportError:
        pass

    try:
        import fitz  # noqa: F401
        import shutil
        import subprocess
        if shutil.which("tesseract"):
            try:
                langs = subprocess.run(
                    ["tesseract", "--list-langs"],
                    capture_output=True, text=True, timeout=5
                ).stdout
                if "jpn" in langs:
                    return "pymupdf"
                else:
                    log.warning("tesseract_no_jpn", hint="Install: apt install tesseract-ocr-jpn")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
    except ImportError:
        pass

    return "none"


def _pdf_to_page_images(pdf_path: Path) -> list[str]:
    """Convert each PDF page to a temporary PNG image. Returns list of paths."""
    import fitz
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="eidp_ocr_")
    image_paths: list[str] = []

    doc = fitz.open(str(pdf_path))
    try:
        for i, page in enumerate(doc):
            # 300 DPI for good OCR quality
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_path = f"{tmp_dir}/page_{i:04d}.png"
            pix.save(img_path)
            image_paths.append(img_path)
    finally:
        doc.close()

    return image_paths


def _ocr_with_paddleocr(pdf_path: Path) -> list[str]:
    """Extract text from image PDF using PaddleOCR PP-OCRv5.

    Requires: pip install paddleocr paddlepaddle
    PP-OCRv5 unified model supports Japanese natively.
    """
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(lang="japan", show_log=False)

    # Convert PDF pages to images first
    try:
        image_paths = _pdf_to_page_images(pdf_path)
    except ImportError:
        log.warning("pymupdf_not_installed", hint="pip install pymupdf (needed for PDF->image)")
        return []

    page_texts: list[str] = []
    for img_path in image_paths:
        result = ocr.ocr(img_path)
        lines: list[str] = []
        if result and result[0]:
            for line_info in result[0]:
                # PaddleOCR returns: [[box], (text, confidence)]
                if len(line_info) >= 2:
                    text = line_info[1][0] if isinstance(line_info[1], (list, tuple)) else str(line_info[1])
                    lines.append(text)
        page_texts.append("\n".join(lines))

    # Cleanup temp images
    import shutil
    if image_paths:
        tmp_dir = str(Path(image_paths[0]).parent)
        shutil.rmtree(tmp_dir, ignore_errors=True)

    log.info("ocr_paddleocr_complete", path=str(pdf_path), pages=len(page_texts),
             total_chars=sum(len(t) for t in page_texts))
    return page_texts


def _ocr_with_pymupdf(pdf_path: Path) -> list[str]:
    """Extract text from image PDF using PyMuPDF's built-in OCR.

    Requires: pip install pymupdf, system Tesseract with jpn language pack.
    Install Tesseract: brew install tesseract tesseract-lang (macOS)
                       apt install tesseract-ocr tesseract-ocr-jpn (Ubuntu)
    """
    import fitz

    page_texts: list[str] = []
    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            tp = page.get_textpage_ocr(language="jpn+eng", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            text = page.get_text(textpage=tp)
            page_texts.append(text)
    finally:
        doc.close()

    log.info("ocr_pymupdf_complete", path=str(pdf_path), pages=len(page_texts),
             total_chars=sum(len(t) for t in page_texts))
    return page_texts


def extract_text_ocr(pdf_path: Path) -> list[str]:
    """Extract text from an image-only PDF using the best available OCR.

    Returns list of page texts (same format as pdfplumber extraction).
    Returns empty list if no OCR provider is available.
    """
    provider = _check_ocr_availability()

    if provider == "none":
        log.warning("no_ocr_available",
                    path=str(pdf_path),
                    hint="Install OCR: pip install paddleocr paddlepaddle")
        return []

    log.info("ocr_start", path=str(pdf_path), provider=provider)

    try:
        if provider == "paddleocr":
            return _ocr_with_paddleocr(pdf_path)
        elif provider == "pymupdf":
            return _ocr_with_pymupdf(pdf_path)
        else:
            return []
    except Exception as e:
        log.warning("ocr_failed", path=str(pdf_path), provider=provider,
                    error=str(e), error_type=type(e).__name__)
        return []
