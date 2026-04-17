"""Quick OCR test script for Venus deployment validation."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eidp.pdf.ocr import extract_text_ocr


def test_pdf(pdf_path: str) -> None:
    path = Path(pdf_path)
    if not path.exists():
        print(f"File not found: {pdf_path}")
        return

    print(f"\n{'='*60}")
    print(f"Testing: {path.name}")
    print(f"{'='*60}")

    pages = extract_text_ocr(path)
    print(f"Extracted {len(pages)} pages")

    for i, pt in enumerate(pages):
        has_dept = any(k in pt for k in ["学科", "分野", "課程"])
        has_enroll = any(k in pt for k in ["生徒", "実員", "定員", "在学者"])
        has_grad = any(k in pt for k in ["卒業", "退学", "中退"])

        marker = ""
        if has_dept and has_enroll:
            marker = " *** ENROLLMENT PAGE ***"
        elif has_grad:
            marker = " (graduation/dropout)"

        print(f"\nPage {i+1}: {len(pt)} chars{marker}")

        # Show enrollment pages in full
        if has_dept and has_enroll:
            print("-" * 40)
            print(pt[:2000])
            print("-" * 40)


if __name__ == "__main__":
    pdfs = sys.argv[1:] or ["/tmp/test_matsumoto.pdf"]
    for pdf in pdfs:
        test_pdf(pdf)
