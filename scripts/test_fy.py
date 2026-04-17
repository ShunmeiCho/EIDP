"""Debug fiscal year detection."""
import os
import sys
import re
from pathlib import Path

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eidp.pdf.ocr import extract_text_ocr
from eidp.pdf.extractor import _clean_ocr_markdown, _norm, _extract_fiscal_year

pdf = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_keisen.pdf"
pages = extract_text_ocr(Path(pdf))
cleaned = [_clean_ocr_markdown(pt) for pt in pages]
full = _norm("\n".join(cleaned))

print(f"=== Year patterns in {pdf} ===")
print(f"令和N年度: {re.findall(r'令和[0-9]+年度', full)[:3]}")
print(f"令和N年: {re.findall(r'令和[0-9]+年', full)[:3]}")
print(f"Western year: {set(re.findall(r'20[2-3][0-9]', full))}")
print(f"Filing date: {re.findall(r'202[0-9][./]\\d{1,2}[./]\\d{1,2}', full)[:3]}")
print(f"R[0-9]: {re.findall(r'(?<![A-Za-z])R[0-9]', full)[:5]}")

fy = _extract_fiscal_year(full)
print(f"\n_extract_fiscal_year returned: {fy!r}")

print("\n=== Page 1 full text ===")
print(cleaned[0][:500])

# Look for any year-like tokens
print("\n=== First 1000 chars of full normalized text ===")
print(full[:1000])
