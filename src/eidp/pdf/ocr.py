"""OCR fallback for image-only PDFs.

Supports multiple OCR backends via provider pattern:
- paddleocr: PaddleOCR PP-OCRv5 (best Japanese accuracy, recommended)
- pymupdf: PyMuPDF built-in OCR (requires Tesseract system install)

The provider is selected automatically based on available packages,
or can be overridden via EIDP_OCR_PROVIDER env var.

Device selection (GPU/CPU):
- Auto-detects CUDA GPU via PaddlePaddle
- Falls back to CPU if no GPU available
- Override via EIDP_OCR_DEVICE env var ("gpu" or "cpu")

Design for portability:
- All OCR deps are optional (ocr extra in pyproject.toml)
- If no OCR is available, returns empty text with a warning
- Output is plain text per page, compatible with parse_pdf's text pipeline
- Model is loaded once per process (singleton) to avoid GPU memory fragmentation
"""

import os
import tempfile
import threading
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

_VALID_PROVIDERS = ("paddleocr", "pymupdf")

# Module-level singleton for PaddleOCR (load once per process)
# Protected by a lock so concurrent first-callers don't double-initialize
_paddleocr_instance: Any | None = None
_paddleocr_lock = threading.Lock()


def _detect_device() -> str:
    """Detect best available device for PaddleOCR. Returns 'gpu' or 'cpu'."""
    override = os.environ.get("EIDP_OCR_DEVICE", "").lower()
    if override in ("gpu", "cpu"):
        return override

    try:
        import paddle
        if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
            return "gpu"
    except Exception:
        pass

    return "cpu"


def _get_paddleocr_instance() -> Any:
    """Get (or create) module-level PaddleOCR instance.

    Loads model once per process to avoid GPU memory fragmentation over
    batch runs and to eliminate repeated model-load overhead.
    Thread-safe via double-checked locking.
    """
    global _paddleocr_instance
    # Fast path: already initialized
    if _paddleocr_instance is not None:
        return _paddleocr_instance

    # Slow path: acquire lock and double-check
    with _paddleocr_lock:
        if _paddleocr_instance is not None:
            return _paddleocr_instance

        from paddleocr import PaddleOCR
        import paddle

        device = _detect_device()
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

        try:
            if device == "gpu":
                paddle.set_device("gpu:0")
            else:
                paddle.set_device("cpu")
        except Exception as e:
            log.warning("paddle_set_device_failed", device=device, error=str(e))

        log.info("ocr_paddleocr_init", device=device,
                 gpu_name=paddle.device.cuda.get_device_name(0) if device == "gpu" else None)

        _paddleocr_instance = PaddleOCR(lang="japan")
        return _paddleocr_instance


def _check_ocr_availability() -> str:
    """Detect available OCR provider. Returns provider name or 'none'."""
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


def _pdf_to_page_images(pdf_path: Path, tmp_dir: str) -> list[str]:
    """Convert each PDF page to a PNG image in tmp_dir. Returns list of paths."""
    import fitz

    image_paths: list[str] = []
    doc = fitz.open(str(pdf_path))
    try:
        for i, page in enumerate(doc):
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            # Limit image size to avoid PaddleOCR resize warnings
            if max(pix.width, pix.height) > 4000:
                scale = 4000 / max(pix.width, pix.height)
                mat = fitz.Matrix(scale * 300 / 72, scale * 300 / 72)
                pix = page.get_pixmap(matrix=mat)
            img_path = f"{tmp_dir}/page_{i:04d}.png"
            pix.save(img_path)
            image_paths.append(img_path)
    finally:
        doc.close()

    return image_paths


def _ocr_with_paddleocr(pdf_path: Path) -> list[str]:
    """Extract text from image PDF using PaddleOCR PP-OCRv5.

    Requires: pip install paddleocr paddlepaddle (or paddlepaddle-gpu)
    PP-OCRv5 unified model supports Japanese natively.
    Uses GPU when available, falls back to CPU automatically.
    Model instance is cached per-process for efficient batch runs.
    """
    ocr = _get_paddleocr_instance()

    # TemporaryDirectory context manager guarantees cleanup on any exit path
    with tempfile.TemporaryDirectory(prefix="eidp_ocr_") as tmp_dir:
        try:
            image_paths = _pdf_to_page_images(pdf_path, tmp_dir)
        except ImportError:
            log.warning("pymupdf_not_installed", hint="pip install pymupdf (needed for PDF->image)")
            return []
        except Exception as e:
            log.warning("pdf_to_image_failed", path=str(pdf_path), error=str(e))
            return []

        page_texts: list[str] = []
        for img_path in image_paths:
            try:
                result = ocr.predict(img_path)
                lines: list[str] = []
                for page_result in result:
                    rec_texts = page_result.get("rec_texts", [])
                    lines.extend(rec_texts)
                page_texts.append("\n".join(lines))
            except Exception as e:
                log.warning("ocr_page_failed", path=img_path, error=str(e))
                page_texts.append("")

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
