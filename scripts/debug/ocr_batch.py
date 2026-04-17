"""Batch OCR test - run pipeline on multiple PDFs and report success rate."""
import os
import sys
import time
from pathlib import Path

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eidp.pdf.ocr import extract_text_ocr
from eidp.pdf.extractor import parse_pdf_ocr


def test_one(pdf_path: Path) -> dict:
    t0 = time.time()
    pages = extract_text_ocr(pdf_path)
    t_ocr = time.time() - t0
    total_chars = sum(len(p) for p in pages)

    if not pages or total_chars < 500:
        return {
            "file": pdf_path.name,
            "pages": len(pages),
            "chars": total_chars,
            "school": "",
            "depts": 0,
            "status": "empty_ocr",
            "t_ocr": t_ocr,
        }

    t0 = time.time()
    try:
        annotation = parse_pdf_ocr(pdf_path, pages)
    except Exception as e:
        return {
            "file": pdf_path.name,
            "pages": len(pages),
            "chars": total_chars,
            "school": "",
            "depts": 0,
            "status": f"parse_error: {type(e).__name__}",
            "t_ocr": t_ocr,
        }
    t_parse = time.time() - t0

    return {
        "file": pdf_path.name,
        "pages": len(pages),
        "chars": total_chars,
        "school": annotation.school_name[:20],
        "depts": len(annotation.departments),
        "status": "ok" if annotation.departments else "no_depts",
        "t_ocr": t_ocr,
        "t_parse": t_parse,
        "deps_with_enrollment": sum(1 for d in annotation.departments if d.enrollment is not None),
    }


if __name__ == "__main__":
    pdf_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/eidp_test_pdfs")
    pdfs = sorted(pdf_dir.glob("*.pdf"))

    print(f"{'File':<30} {'Pages':>5} {'Chars':>7} {'OCR_s':>6} {'School':<22} {'Depts':>5} {'Enr':>4} Status")
    print("-" * 110)

    results = []
    for pdf in pdfs:
        r = test_one(pdf)
        results.append(r)
        enr = r.get("deps_with_enrollment", 0)
        print(f"{r['file']:<30} {r['pages']:>5} {r['chars']:>7} {r['t_ocr']:>6.1f} "
              f"{r['school']:<22} {r['depts']:>5} {enr:>4} {r['status']}")

    print("\n" + "=" * 60)
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "ok")
    total_depts = sum(r["depts"] for r in results)
    total_enr = sum(r.get("deps_with_enrollment", 0) for r in results)
    print(f"Total: {total} | OK: {ok} ({100*ok/total:.0f}%) | "
          f"Depts: {total_depts} | With enrollment: {total_enr}")
