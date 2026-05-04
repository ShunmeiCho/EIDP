"""Sprint 8.6.c — OCR add-on package.

Image-PDF rescue path. Add-on ZIP carries the Tesseract binary and
``jpn.traineddata``; this package wraps both behind a small functional
surface that ``ingest.py`` (Sprint 8.6.d) can call without learning
about subprocesses or hardware-detection logic.
"""

from __future__ import annotations

from eidp.ocr.availability import (
    OcrAvailability,
    availability_banner_severity,
    availability_banner_text,
    detect_ocr_availability,
)
from eidp.ocr.runtime_detect import RuntimeProfile, detect_runtime, ocr_auto_enable
from eidp.ocr.tesseract import (
    OcrBinaryNotFoundError,
    OcrError,
    OcrPageResult,
    OcrWord,
    locate_tessdata,
    locate_tesseract,
    parse_tesseract_tsv,
    run_tesseract_on_image,
)

__all__ = [
    "OcrAvailability",
    "OcrBinaryNotFoundError",
    "OcrError",
    "OcrPageResult",
    "OcrWord",
    "RuntimeProfile",
    "availability_banner_severity",
    "availability_banner_text",
    "detect_ocr_availability",
    "detect_runtime",
    "locate_tessdata",
    "locate_tesseract",
    "ocr_auto_enable",
    "parse_tesseract_tsv",
    "run_tesseract_on_image",
]
