"""Debug _parse_department_section directly."""
import os
import sys
import unicodedata
from pathlib import Path

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eidp.pdf.ocr import extract_text_ocr
from eidp.pdf.extractor import _clean_ocr_markdown, _parse_department_section, _norm

path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_matsumoto.pdf")
pages = extract_text_ocr(path)
cleaned = [_clean_ocr_markdown(pt) for pt in pages]
normed = [_norm(pt) for pt in cleaned]

# Find dept sections (same logic as parse_pdf_ocr)
dept_starts = []
for i, pt in enumerate(normed):
    markers = sum(["分野" in pt, "学科名" in pt, "生徒総定員" in pt])
    is_fin = "財務" in pt or "経営情報の公表" in pt
    if markers >= 2 and not is_fin:
        dept_starts.append(i)

print(f"Dept section starts: {dept_starts}")

for idx, start in enumerate(dept_starts):
    end = dept_starts[idx + 1] if idx + 1 < len(dept_starts) else len(normed)
    section = "\n".join(normed[start:end])
    print(f"\nSection {idx+1} (pages {start+1}-{end}): {len(section)} chars")

    result = _parse_department_section(section)
    if result is None:
        print("  RESULT: None")
        # Show what was found
        lines = section.split("\n")
        for lno, line in enumerate(lines):
            if any(k in line for k in ["学科名", "分野", "定員", "実員", "40人", "30人", "卒業"]):
                print(f"  Line {lno}: {line}")
    else:
        print(f"  RESULT: {result.dept_name} cap={result.capacity} enr={result.enrollment}")
