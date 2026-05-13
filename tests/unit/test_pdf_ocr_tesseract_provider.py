from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from eidp.pdf import ocr as pdf_ocr


def test_extract_text_ocr_uses_tesseract_wrapper(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 image")
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"png")
    binary = tmp_path / "ocr-addon" / "tesseract" / "tesseract.exe"
    tessdata = tmp_path / "ocr-addon" / "tessdata"
    binary.parent.mkdir(parents=True)
    tessdata.mkdir(parents=True)
    binary.write_bytes(b"PE")
    (tessdata / "jpn.traineddata").write_bytes(b"jpn")

    calls: dict[str, object] = {}

    monkeypatch.setenv("EIDP_OCR_PROVIDER", "tesseract")
    monkeypatch.setattr(
        pdf_ocr,
        "_pdf_to_page_images",
        lambda seen_pdf, tmp_dir: calls.setdefault("pdf", seen_pdf) and [str(image_path)],
    )
    monkeypatch.setattr(pdf_ocr, "locate_tesseract", lambda *, app_root=None, env=None: binary)
    monkeypatch.setattr(pdf_ocr, "locate_tessdata", lambda *, app_root=None, env=None: tessdata)

    def fake_run(image, *, binary=None, tessdata_dir=None, lang="jpn+eng", psm=6, runner=None):
        calls["image"] = image
        calls["binary"] = binary
        calls["tessdata_dir"] = tessdata_dir
        calls["lang"] = lang
        calls["psm"] = psm
        return SimpleNamespace(full_text="令和8年度\n対象比率 100", conf_values=[95, 90])

    monkeypatch.setattr(pdf_ocr, "run_tesseract_on_image", fake_run)

    assert pdf_ocr.extract_text_ocr(pdf_path) == ["令和8年度\n対象比率 100"]
    assert calls == {
        "pdf": pdf_path,
        "image": image_path,
        "binary": binary,
        "tessdata_dir": tessdata,
        "lang": "jpn+eng",
        "psm": 6,
    }
