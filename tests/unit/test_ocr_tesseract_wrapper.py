"""Sprint 8.6.c — Tesseract wrapper + TSV parser regression."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from eidp.extraction_confidence import compute_f1_ocr_tesseract
from eidp.ocr.tesseract import (
    OcrBinaryNotFoundError,
    OcrError,
    OcrPageResult,
    OcrWord,
    locate_tessdata,
    locate_tesseract,
    parse_tesseract_tsv,
    run_tesseract_on_image,
)

# ---------------------------------------------------------------------------
# locate_tesseract
# ---------------------------------------------------------------------------


def test_locate_tesseract_uses_env_override(tmp_path: Path):
    binary = tmp_path / "fake-tess"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)

    resolved = locate_tesseract(env={"EIDP_TESSERACT_BIN": str(binary)})
    assert resolved == binary


def test_locate_tesseract_env_override_must_exist(tmp_path: Path):
    with pytest.raises(OcrBinaryNotFoundError, match="does not exist"):
        locate_tesseract(env={"EIDP_TESSERACT_BIN": str(tmp_path / "nope")})


def test_locate_tesseract_prefers_project_runtime_over_path(tmp_path: Path):
    """The project runtime wins over PATH so dev hosts do not affect deployment."""
    runtime = tmp_path / "ocr" / "tesseract" / "bin"
    runtime.mkdir(parents=True)
    binary = runtime / "tesseract"
    binary.write_bytes(b"ELF")

    resolved = locate_tesseract(app_root=tmp_path, env={})
    assert resolved == binary


def test_locate_tesseract_falls_back_to_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No env override or project runtime means use shutil.which."""
    fake_bin = tmp_path / "tesseract-shim"
    fake_bin.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "eidp.ocr.tesseract.shutil.which",
        lambda _name: str(fake_bin),
    )
    resolved = locate_tesseract(env={})
    assert resolved == fake_bin


def test_locate_tesseract_raises_when_nothing_found(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("eidp.ocr.tesseract.shutil.which", lambda _name: None)
    with pytest.raises(OcrBinaryNotFoundError, match="not found"):
        locate_tesseract(env={})


# ---------------------------------------------------------------------------
# locate_tessdata
# ---------------------------------------------------------------------------


def test_locate_tessdata_prefers_env(tmp_path: Path):
    env_dir = tmp_path / "td-env"
    env_dir.mkdir()
    (env_dir / "jpn.traineddata").write_bytes(b"x")
    resolved = locate_tessdata(env={"TESSDATA_PREFIX": str(env_dir)})
    assert resolved == env_dir


def test_locate_tessdata_falls_back_to_project_runtime(tmp_path: Path):
    runtime = tmp_path / "ocr" / "tessdata"
    runtime.mkdir(parents=True)
    (runtime / "jpn.traineddata").write_bytes(b"x")
    resolved = locate_tessdata(app_root=tmp_path, env={})
    assert resolved == runtime


def test_locate_tessdata_returns_none_when_missing(tmp_path: Path):
    assert locate_tessdata(app_root=tmp_path, env={}) is None


# ---------------------------------------------------------------------------
# parse_tesseract_tsv
# ---------------------------------------------------------------------------


_HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"


def _tsv(rows: list[list[str]]) -> str:
    return _HEADER + "\n" + "\n".join("\t".join(r) for r in rows)


def test_parse_tsv_extracts_word_rows():
    tsv = _tsv([
        ["1", "1", "1", "1", "1", "0", "0", "0", "100", "20", "-1", ""],
        ["5", "1", "1", "1", "1", "1", "10", "10", "30", "20", "92", "学科"],
        ["5", "1", "1", "1", "1", "2", "50", "10", "30", "20", "78", "名"],
    ])
    result = parse_tesseract_tsv(tsv)
    assert isinstance(result, OcrPageResult)
    assert len(result.words) == 2
    assert [w.text for w in result.words] == ["学科", "名"]
    assert [w.conf for w in result.words] == [92, 78]
    assert result.full_text == "学科 名"


def test_parse_tsv_preserves_negative_one_sentinel():
    """Tokens Tesseract gave up on emit conf=-1 with empty text. Keep
    them in the OcrPageResult so the F1 calculation can drop them
    explicitly per Sprint 8.6.a contract."""
    tsv = _tsv([
        ["5", "1", "1", "1", "1", "1", "0", "0", "10", "10", "-1", ""],
        ["5", "1", "1", "1", "1", "2", "0", "0", "10", "10", "85", "OK"],
    ])
    result = parse_tesseract_tsv(tsv)
    assert [w.conf for w in result.words] == [-1, 85]
    assert result.usable_words == [
        OcrWord(text="OK", conf=85, line_num=1, word_num=2,
                left=0, top=0, width=10, height=10),
    ]


def test_parse_tsv_empty_input_returns_empty_result():
    assert parse_tesseract_tsv("").words == []
    assert parse_tesseract_tsv("   \n").words == []


def test_parse_tsv_missing_columns_raises():
    with pytest.raises(OcrError, match="missing columns"):
        parse_tesseract_tsv("level\ttext\n5\thi\n")


def test_parse_tsv_drops_malformed_numeric_cells():
    """A bad row must not take down the rest. Tesseract on noisy
    scans occasionally emits malformed bbox values."""
    tsv = _tsv([
        ["5", "1", "1", "1", "1", "1", "x", "y", "z", "w", "85", "OK"],
        ["5", "1", "1", "1", "1", "2", "0", "0", "10", "10", "70", "B"],
    ])
    result = parse_tesseract_tsv(tsv)
    assert len(result.words) == 1
    assert result.words[0].text == "B"


def test_parse_tsv_full_text_orders_by_line():
    tsv = _tsv([
        ["5", "1", "1", "1", "2", "1", "0", "0", "10", "10", "90", "second"],
        ["5", "1", "1", "1", "1", "1", "0", "0", "10", "10", "90", "first"],
    ])
    result = parse_tesseract_tsv(tsv)
    assert result.full_text == "first\nsecond"


# ---------------------------------------------------------------------------
# run_tesseract_on_image
# ---------------------------------------------------------------------------


def _stub_runner(stdout: str, *, returncode: int = 0, stderr: str = ""):
    def _run(_cmd: list[str]):
        return subprocess.CompletedProcess(
            args=_cmd, returncode=returncode, stdout=stdout, stderr=stderr,
        )
    return _run


def test_run_tesseract_returns_page_result(tmp_path: Path):
    img = tmp_path / "p1.png"
    img.write_bytes(b"\x89PNG\r\n")
    tsv = _tsv([
        ["5", "1", "1", "1", "1", "1", "0", "0", "10", "10", "90", "学科"],
    ])
    result = run_tesseract_on_image(
        img, binary=Path("tesseract"), runner=_stub_runner(tsv),
    )
    assert len(result.words) == 1


def test_run_tesseract_passes_psm_and_lang(tmp_path: Path):
    img = tmp_path / "p2.png"
    img.write_bytes(b"\x89PNG\r\n")
    captured: dict[str, list[str]] = {}

    def _run(cmd):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    run_tesseract_on_image(
        img, binary=Path("/abs/tesseract"), lang="jpn", psm=4, runner=_run,
    )
    cmd = captured["cmd"]
    assert cmd[0] == "/abs/tesseract"
    assert "-l" in cmd and cmd[cmd.index("-l") + 1] == "jpn"
    assert "--psm" in cmd and cmd[cmd.index("--psm") + 1] == "4"
    assert cmd[-1] == "tsv"


def test_run_tesseract_threads_tessdata_dir(tmp_path: Path):
    img = tmp_path / "p3.png"
    img.write_bytes(b"\x89PNG\r\n")
    captured: dict[str, list[str]] = {}

    def _run(cmd):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    run_tesseract_on_image(
        img, binary=Path("tesseract"), tessdata_dir=Path("/td"),
        runner=_run,
    )
    cmd = captured["cmd"]
    idx = cmd.index("--tessdata-dir")
    assert cmd[idx + 1] == "/td"


def test_run_tesseract_raises_on_nonzero_exit(tmp_path: Path):
    img = tmp_path / "p4.png"
    img.write_bytes(b"\x89PNG\r\n")
    with pytest.raises(OcrError, match="rc=2"):
        run_tesseract_on_image(
            img, binary=Path("tesseract"),
            runner=_stub_runner("", returncode=2, stderr="bad image"),
        )


def test_run_tesseract_missing_image_raises(tmp_path: Path):
    with pytest.raises(OcrError, match="does not exist"):
        run_tesseract_on_image(
            tmp_path / "no-such.png", binary=Path("tesseract"),
            runner=_stub_runner(""),
        )


# ---------------------------------------------------------------------------
# Plumbing into compute_f1_ocr_tesseract (Sprint 8.6.a)
# ---------------------------------------------------------------------------


def test_ocr_page_result_feeds_f1_computation(tmp_path: Path):
    """End-to-end Sprint 8.6.c × 8.6.a wiring: TSV → page result → F1.
    Exercise the contract that ``compute_f1_ocr_tesseract`` drops -1
    sentinels."""
    tsv = _tsv([
        ["5", "1", "1", "1", "1", "1", "0", "0", "10", "10", "90", "OK"],
        ["5", "1", "1", "1", "1", "2", "0", "0", "10", "10", "-1", ""],
        ["5", "1", "1", "1", "1", "3", "0", "0", "10", "10", "70", "B"],
    ])
    result = parse_tesseract_tsv(tsv)
    f1 = compute_f1_ocr_tesseract(result.conf_values)
    # Mean of (90, -1, 70) drops -1 → mean(90, 70) = 80 → 0.8
    assert f1 == pytest.approx(0.8, abs=1e-6)
