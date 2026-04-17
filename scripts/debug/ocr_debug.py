"""Debug OCR parsing - show what the parser sees."""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eidp.pdf.ocr import extract_text_ocr
from eidp.pdf.extractor import _clean_ocr_markdown, _norm


def debug_parse(pdf_path: str) -> None:
    path = Path(pdf_path)
    pages = extract_text_ocr(path)
    cleaned = [_clean_ocr_markdown(pt) for pt in pages]
    normed = [_norm(pt) for pt in cleaned]

    print(f"Pages: {len(pages)}")
    for i, pt in enumerate(normed):
        markers = sum([
            "分野" in pt,
            "学科名" in pt,
            "生徒総定員" in pt,
        ])
        is_financial = "財務" in pt or "経営情報の公表" in pt
        has_enrollment = "生徒実員" in pt or "在学者数" in pt

        print(f"\nPage {i+1}: markers={markers}, financial={is_financial}, has_enrollment={has_enrollment}")
        if markers >= 1:
            # Show lines containing markers
            for line in pt.split("\n"):
                if any(k in line for k in ["分野", "学科名", "生徒総定員", "生徒実員", "定員"]):
                    print(f"  >>> {line}")


if __name__ == "__main__":
    import os
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    pdfs = sys.argv[1:] or ["/tmp/test_matsumoto.pdf"]
    for pdf in pdfs:
        debug_parse(pdf)
