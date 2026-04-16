"""End-to-end OCR pipeline test: PDF -> OCR -> parse -> structured data."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eidp.pdf.ocr import extract_text_ocr
from eidp.pdf.extractor import parse_pdf_ocr


def test_pipeline(pdf_path: str) -> None:
    path = Path(pdf_path)
    if not path.exists():
        print(f"File not found: {pdf_path}")
        return

    print(f"\n{'='*60}")
    print(f"Pipeline test: {path.name}")
    print(f"{'='*60}")

    # Step 1: OCR
    print("\n[Step 1] Running OCR...")
    pages = extract_text_ocr(path)
    print(f"  OCR extracted {len(pages)} pages, {sum(len(p) for p in pages)} total chars")

    if not pages or not any(p.strip() for p in pages):
        print("  FAILED: No text extracted")
        return

    # Step 2: Parse structured data
    print("\n[Step 2] Parsing enrollment data...")
    annotation = parse_pdf_ocr(path, pages)

    # Step 3: Report results
    print(f"\n[Results]")
    print(f"  School name: {annotation.school_name}")
    print(f"  Operator:    {annotation.operator_name}")
    print(f"  Fiscal year: {annotation.fiscal_year}")
    print(f"  Departments: {len(annotation.departments)}")

    for i, dept in enumerate(annotation.departments):
        print(f"\n  Department {i+1}:")
        print(f"    Name:       {dept.dept_name}")
        print(f"    Course:     {dept.course_name}")
        print(f"    Duration:   {dept.duration_years}y {'Day' if dept.is_daytime else 'Night'}")
        print(f"    Capacity:   {dept.capacity}")
        print(f"    Enrollment: {dept.enrollment}")
        print(f"    Foreign:    {dept.foreign_students}")
        print(f"    Graduates:  {dept.graduates}")
        print(f"    Dropouts:   {dept.dropouts}")

    if annotation.support_recipient:
        sr = annotation.support_recipient
        print(f"\n  Support Recipient:")
        print(f"    Exempt:     {sr.exempt_count}")
        print(f"    Scholarship: {sr.scholarship_count}")


if __name__ == "__main__":
    pdfs = sys.argv[1:] or ["/tmp/test_matsumoto.pdf"]
    for pdf in pdfs:
        test_pipeline(pdf)
