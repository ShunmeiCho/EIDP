"""Show raw OCR text for enrollment pages."""
import os
import sys
import unicodedata
from pathlib import Path

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eidp.pdf.ocr import extract_text_ocr
from eidp.pdf.extractor import _clean_ocr_markdown


def _norm(text):
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_matsumoto.pdf")
pages = extract_text_ocr(path)
cleaned = [_clean_ocr_markdown(pt) for pt in pages]
normed = [_norm(pt) for pt in cleaned]

# Show pages 5, 7, 9 (enrollment pages)
for idx in [4, 6, 8]:  # 0-indexed
    if idx < len(normed):
        print(f"\n{'='*60}")
        print(f"PAGE {idx+1} (full normed text)")
        print(f"{'='*60}")
        for lno, line in enumerate(normed[idx].split("\n")):
            print(f"  {lno:3d}: {line}")
