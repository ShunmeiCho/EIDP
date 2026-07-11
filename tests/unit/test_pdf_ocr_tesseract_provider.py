from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

from eidp.pdf import ocr as pdf_ocr


def test_extract_text_ocr_uses_tesseract_wrapper(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 image")
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"png")
    binary = tmp_path / "ocr" / "tesseract" / "bin" / "tesseract"
    tessdata = tmp_path / "ocr" / "tessdata"
    binary.parent.mkdir(parents=True)
    tessdata.mkdir(parents=True)
    binary.write_bytes(b"ELF")
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


def test_detect_device_honors_env_override(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_OCR_DEVICE", "GPU")
    assert pdf_ocr._detect_device() == "gpu"

    monkeypatch.setenv("EIDP_OCR_DEVICE", "cpu")
    assert pdf_ocr._detect_device() == "cpu"


def test_extract_text_ocr_result_routes_providers_and_handles_failures(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(pdf_ocr, "_check_ocr_availability", lambda: "none")
    assert pdf_ocr.extract_text_ocr_result(pdf_path) == pdf_ocr.OcrExtraction(
        page_texts=[],
        provider="none",
        conf_values=[],
    )

    monkeypatch.setattr(pdf_ocr, "_check_ocr_availability", lambda: "paddleocr")
    monkeypatch.setattr(pdf_ocr, "_ocr_with_paddleocr", lambda path: ["paddle text"])
    assert pdf_ocr.extract_text_ocr_result(pdf_path) == pdf_ocr.OcrExtraction(
        page_texts=["paddle text"],
        provider="paddleocr",
        conf_values=[],
    )

    monkeypatch.setattr(pdf_ocr, "_check_ocr_availability", lambda: "pymupdf")
    monkeypatch.setattr(pdf_ocr, "_ocr_with_pymupdf", lambda path: ["pymupdf text"])
    assert pdf_ocr.extract_text_ocr_result(pdf_path).page_texts == ["pymupdf text"]

    monkeypatch.setattr(pdf_ocr, "_check_ocr_availability", lambda: "tesseract")
    monkeypatch.setattr(
        pdf_ocr,
        "_ocr_with_tesseract",
        lambda path: pdf_ocr.OcrExtraction(page_texts=["tsv text"], provider="tesseract", conf_values=[92]),
    )
    assert pdf_ocr.extract_text_ocr_result(pdf_path) == pdf_ocr.OcrExtraction(
        page_texts=["tsv text"],
        provider="tesseract",
        conf_values=[92],
    )

    monkeypatch.setattr(pdf_ocr, "_check_ocr_availability", lambda: "custom")
    assert pdf_ocr.extract_text_ocr_result(pdf_path) == pdf_ocr.OcrExtraction(
        page_texts=[],
        provider="custom",
        conf_values=[],
    )

    monkeypatch.setattr(pdf_ocr, "_check_ocr_availability", lambda: "paddleocr")

    def fail_paddle(path: Path) -> list[str]:
        raise RuntimeError("model failed")

    monkeypatch.setattr(pdf_ocr, "_ocr_with_paddleocr", fail_paddle)
    assert pdf_ocr.extract_text_ocr_result(pdf_path) == pdf_ocr.OcrExtraction(
        page_texts=[],
        provider="paddleocr",
        conf_values=[],
    )


def test_ocr_with_paddleocr_extracts_text_and_handles_pdf_conversion_error(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    class FakePaddleOcr:
        def predict(self, image_path: str) -> list[dict[str, list[str]]]:
            if image_path.endswith("page2.png"):
                raise RuntimeError("bad page")
            return [{"rec_texts": ["令和8年度", "対象比率"]}]

    monkeypatch.setattr(pdf_ocr, "_get_paddleocr_instance", lambda: FakePaddleOcr())
    monkeypatch.setattr(
        pdf_ocr,
        "_pdf_to_page_images",
        lambda seen_pdf, tmp_dir: [f"{tmp_dir}/page1.png", f"{tmp_dir}/page2.png"],
    )

    assert pdf_ocr._ocr_with_paddleocr(pdf_path) == ["令和8年度\n対象比率", ""]

    monkeypatch.setattr(
        pdf_ocr,
        "_pdf_to_page_images",
        lambda seen_pdf, tmp_dir: (_ for _ in ()).throw(RuntimeError("convert failed")),
    )
    assert pdf_ocr._ocr_with_paddleocr(pdf_path) == []


def test_ocr_with_tesseract_collects_confidences_and_keeps_failed_page_blank(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    binary = tmp_path / "tesseract"
    tessdata = tmp_path / "tessdata"
    binary.write_bytes(b"ELF")
    tessdata.mkdir()

    monkeypatch.setattr(pdf_ocr, "locate_tesseract", lambda *, app_root=None, env=None: binary)
    monkeypatch.setattr(pdf_ocr, "locate_tessdata", lambda *, app_root=None, env=None: tessdata)
    monkeypatch.setattr(
        pdf_ocr,
        "_pdf_to_page_images",
        lambda seen_pdf, tmp_dir: [f"{tmp_dir}/page1.png", f"{tmp_dir}/page2.png"],
    )

    def fake_run(image: Path, **kwargs):
        if image.name == "page2.png":
            raise pdf_ocr.OcrError("ocr failed")
        return SimpleNamespace(full_text="OCR text", conf_values=[95, -1, 88])

    monkeypatch.setattr(pdf_ocr, "run_tesseract_on_image", fake_run)

    assert pdf_ocr._ocr_with_tesseract(pdf_path) == pdf_ocr.OcrExtraction(
        page_texts=["OCR text", ""],
        provider="tesseract",
        conf_values=[95, -1, 88],
    )


def test_ocr_with_tesseract_returns_empty_when_pdf_conversion_unavailable(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(pdf_ocr, "locate_tesseract", lambda *, app_root=None, env=None: tmp_path / "tesseract")
    monkeypatch.setattr(pdf_ocr, "locate_tessdata", lambda *, app_root=None, env=None: tmp_path / "tessdata")
    monkeypatch.setattr(
        pdf_ocr,
        "_pdf_to_page_images",
        lambda seen_pdf, tmp_dir: (_ for _ in ()).throw(ImportError("missing fitz")),
    )

    assert pdf_ocr._ocr_with_tesseract(pdf_path) == pdf_ocr.OcrExtraction(
        page_texts=[],
        provider="tesseract",
        conf_values=[],
    )


def test_check_ocr_availability_honors_valid_provider_override(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_OCR_PROVIDER", "pymupdf")

    assert pdf_ocr._check_ocr_availability() == "pymupdf"


def test_check_ocr_availability_returns_none_when_core_modules_missing(monkeypatch) -> None:
    monkeypatch.delenv("EIDP_OCR_PROVIDER", raising=False)

    real_import = __import__

    def fake_import(name: str, *args, **kwargs):
        if name in {"paddleocr", "fitz"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    assert pdf_ocr._check_ocr_availability() == "none"


def test_get_paddleocr_instance_initializes_once_and_uses_detected_gpu(monkeypatch) -> None:
    monkeypatch.delenv("EIDP_OCR_DEVICE", raising=False)
    monkeypatch.setattr(pdf_ocr, "_paddleocr_instance", None)
    set_device_calls: list[str] = []

    paddle = types.ModuleType("paddle")

    class FakeCuda:
        @staticmethod
        def device_count() -> int:
            return 1

        @staticmethod
        def get_device_name(index: int) -> str:
            assert index == 0
            return "Fake GPU"

    class FakeDevice:
        cuda = FakeCuda()

        @staticmethod
        def is_compiled_with_cuda() -> bool:
            return True

    def fake_set_device(device: str) -> None:
        set_device_calls.append(device)

    paddle.device = FakeDevice()
    paddle.set_device = fake_set_device

    paddleocr = types.ModuleType("paddleocr")

    class FakePaddleOCR:
        def __init__(self, *, lang: str) -> None:
            self.lang = lang

    paddleocr.PaddleOCR = FakePaddleOCR
    monkeypatch.setitem(sys.modules, "paddle", paddle)
    monkeypatch.setitem(sys.modules, "paddleocr", paddleocr)

    first = pdf_ocr._get_paddleocr_instance()
    second = pdf_ocr._get_paddleocr_instance()

    assert first is second
    assert first.lang == "japan"
    assert set_device_calls == ["gpu:0"]
    assert pdf_ocr.os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] == "True"

    monkeypatch.setattr(pdf_ocr, "_paddleocr_instance", None)


def test_pdf_to_page_images_renders_pages_and_downscales_large_pixmaps(monkeypatch, tmp_path: Path) -> None:
    saved: list[Path] = []

    class FakePixmap:
        def __init__(self, *, width: int, height: int) -> None:
            self.width = width
            self.height = height

        def save(self, path: str) -> None:
            out = Path(path)
            out.write_bytes(b"png")
            saved.append(out)

    class FakePage:
        def __init__(self, *, large: bool) -> None:
            self.large = large
            self.calls = 0

        def get_pixmap(self, *, matrix):
            self.calls += 1
            if self.large and self.calls == 1:
                return FakePixmap(width=5000, height=3000)
            return FakePixmap(width=1200, height=900)

    class FakeDoc:
        def __init__(self) -> None:
            self.pages = [FakePage(large=True), FakePage(large=False)]
            self.closed = False

        def __iter__(self):
            return iter(self.pages)

        def close(self) -> None:
            self.closed = True

    fake_doc = FakeDoc()
    fitz = types.ModuleType("fitz")
    fitz.Matrix = lambda width, height: (width, height)
    fitz.open = lambda path: fake_doc
    monkeypatch.setitem(sys.modules, "fitz", fitz)

    images = pdf_ocr._pdf_to_page_images(tmp_path / "image.pdf", str(tmp_path))

    assert images == [str(tmp_path / "page_0000.png"), str(tmp_path / "page_0001.png")]
    assert saved == [tmp_path / "page_0000.png", tmp_path / "page_0001.png"]
    assert fake_doc.closed is True
    assert fake_doc.pages[0].calls == 2
    assert fake_doc.pages[1].calls == 1


def test_ocr_with_pymupdf_extracts_each_page_and_closes_document(monkeypatch, tmp_path: Path) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text

        def get_textpage_ocr(self, *, language: str, flags: int) -> str:
            assert language == "jpn+eng"
            assert flags == 16
            return f"textpage:{self.text}"

        def get_text(self, *, textpage: str) -> str:
            return textpage.replace("textpage:", "")

    class FakeDoc:
        def __init__(self) -> None:
            self.closed = False

        def __iter__(self):
            return iter([FakePage("one"), FakePage("two")])

        def close(self) -> None:
            self.closed = True

    fake_doc = FakeDoc()
    fitz = types.ModuleType("fitz")
    fitz.TEXT_PRESERVE_WHITESPACE = 16
    fitz.open = lambda path: fake_doc
    monkeypatch.setitem(sys.modules, "fitz", fitz)

    assert pdf_ocr._ocr_with_pymupdf(tmp_path / "image.pdf") == ["one", "two"]
    assert fake_doc.closed is True
