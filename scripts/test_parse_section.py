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

    # Manually run the same logic to see what values get extracted
    import re
    lines = section.split("\n")
    normed_lines = [_norm(l) for l in lines]

    # Check dept_name extraction
    dept_name = ""
    for i, ln in enumerate(normed_lines):
        header_same = "学科名" in ln and ("分野" in ln or "課程名" in ln)
        header_ocr = (
            "学科名" in ln
            and "分野" not in ln
            and any("分野" in normed_lines[k] for k in range(max(0, i - 3), i))
        )
        if header_same or header_ocr:
            print(f"  DEPT HEADER at line {i}: same={header_same} ocr={header_ocr}")
            for j in range(i + 1, min(i + 5, len(normed_lines))):
                c = normed_lines[j].strip()
                print(f"    Candidate line {j}: '{c}'")
            break

    # Check enrollment extraction
    for i, ln in enumerate(normed_lines):
        if "生徒総定員" in ln:
            print(f"  ENROLL HEADER at line {i}: '{ln}'")
            for j in range(i + 1, min(i + 15, len(normed_lines))):
                dl = normed_lines[j]
                pm = re.findall(r"(\d+)\s*人", dl)
                v0 = re.match(r"^[VOYvo]\s*0$", dl.strip())
                if pm or v0:
                    print(f"    Data line {j}: '{dl}' -> nums={pm} v0={bool(v0)}")
            break

    result = _parse_department_section(section)
    if result is None:
        print("  RESULT: None (dept_name or enrollment missing)")
    else:
        print(f"  RESULT: {result.dept_name} cap={result.capacity} enr={result.enrollment}")
