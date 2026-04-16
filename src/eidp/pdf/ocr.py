"""OCR fallback for image-only PDFs.

Supports multiple OCR backends via provider pattern:
- pymupdf: PyMuPDF built-in OCR (requires Tesseract system install)
- mineru: MinerU pipeline (best accuracy, requires magic-pdf package)

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


def _check_ocr_availability() -> str:
    """Detect available OCR provider. Returns provider name or 'none'."""
    import os

    # Allow explicit override
    override = os.environ.get("EIDP_OCR_PROVIDER", "").lower()
    if override in ("pymupdf", "mineru"):
        return override

    # Auto-detect: prefer MinerU > PyMuPDF OCR
    try:
        from magic_pdf.pipe.UNIPipe import UNIPipe  # noqa: F401
        return "mineru"
    except ImportError:
        pass

    try:
        import fitz  # noqa: F401
        # PyMuPDF can do OCR if Tesseract is installed with Japanese language
        import shutil
        import subprocess
        if shutil.which("tesseract"):
            # Verify Japanese language pack is available
            try:
                langs = subprocess.run(
                    ["tesseract", "--list-langs"],
                    capture_output=True, text=True, timeout=5
                ).stdout
                if "jpn" in langs:
                    return "pymupdf"
                else:
                    log.warning("tesseract_no_jpn", hint="Install: brew install tesseract-lang (macOS) or apt install tesseract-ocr-jpn")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
    except ImportError:
        pass

    return "none"


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
            # Use PyMuPDF's built-in OCR with Japanese language
            tp = page.get_textpage_ocr(language="jpn+eng", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            text = page.get_text(textpage=tp)
            page_texts.append(text)
    finally:
        doc.close()

    log.info("ocr_pymupdf_complete", path=str(pdf_path), pages=len(page_texts),
             total_chars=sum(len(t) for t in page_texts))
    return page_texts


def _ocr_with_mineru(pdf_path: Path) -> list[str]:
    """Extract text from image PDF using MinerU pipeline.

    Requires: pip install magic-pdf[full]
    Best accuracy for Japanese tabular documents.
    """
    try:
        from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
    except ImportError:
        log.error("mineru_not_installed", hint="Install: pip install magic-pdf")
        return []

    import re
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="mineru_")

    try:
        # MinerU v1.x API: uses Dataset + FileBasedDataWriter
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter
        from magic_pdf.data.dataset import PymuDocDataset

        pdf_bytes = Path(pdf_path).read_bytes()
        image_writer = FileBasedDataWriter(tmp_dir)

        dataset = PymuDocDataset(pdf_bytes)
        model_json = doc_analyze(dataset, ocr=True, lang="ja")

        # Use OCR pipe for image-only PDFs
        pipe_result = dataset.apply(model_json, image_writer, is_ocr=True)
        md_content = pipe_result.get_markdown(image_writer)

    except ImportError:
        # Fallback: MinerU v0.6.x API
        try:
            from magic_pdf.pipe.UNIPipe import UNIPipe
            from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter

            pdf_bytes = Path(pdf_path).read_bytes()
            image_writer = DiskReaderWriter(tmp_dir)

            model_json = doc_analyze(pdf_bytes)
            pipe = UNIPipe(pdf_bytes, model_json, image_writer=image_writer)
            pipe.pipe_classify()
            pipe.pipe_analyze()
            pipe.pipe_parse()

            result = pipe.pipe_mk_markdown(image_writer)
            md_content = result[0] if isinstance(result, tuple) else result
        except Exception as e:
            log.warning("mineru_v06_failed", error=str(e))
            md_content = ""

    # Split by page markers
    if md_content:
        pages = re.split(r"\n---\n|\n\f\n", md_content)
        page_texts = [p.strip() for p in pages if p.strip()]
        if not page_texts:
            page_texts = [md_content]
    else:
        page_texts = []

    # Cleanup temp dir
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    log.info("ocr_mineru_complete", path=str(pdf_path), pages=len(page_texts),
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
                    hint="Install OCR: uv sync --extra ocr (requires Tesseract for pymupdf)")
        return []

    log.info("ocr_start", path=str(pdf_path), provider=provider)

    try:
        if provider == "mineru":
            return _ocr_with_mineru(pdf_path)
        elif provider == "pymupdf":
            return _ocr_with_pymupdf(pdf_path)
        else:
            return []
    except Exception as e:
        log.warning("ocr_failed", path=str(pdf_path), provider=provider,
                    error=str(e), error_type=type(e).__name__)
        return []
