from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eidp.cli import app
from eidp.pdf.schema import DepartmentRecord, SchoolAnnotation


def test_eval_pdf_runs_current_parser(monkeypatch, tmp_path: Path) -> None:
    gold_dir = tmp_path / "gold"
    pdf_dir = tmp_path / "pdfs"
    gold_dir.mkdir()
    pdf_dir.mkdir()
    (pdf_dir / "sample.pdf").write_bytes(b"%PDF-1.4\n")

    annotation = SchoolAnnotation(
        school_name="テスト専門学校",
        fiscal_year="令和7年度",
        source_pdf="sample.pdf",
        departments=[
            DepartmentRecord(
                name="情報処理科",
                course_name="専門課程",
                duration_years=2,
                day_or_evening="昼",
                capacity=40,
                enrollment=38,
            )
        ],
    )
    (gold_dir / "sample.json").write_text(
        json.dumps(annotation.model_dump(), ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_parse_pdf(pdf_path: Path) -> SchoolAnnotation:
        assert pdf_path == pdf_dir / "sample.pdf"
        return annotation

    monkeypatch.setattr("eidp.pdf.extractor.parse_pdf", fake_parse_pdf)

    result = CliRunner().invoke(
        app,
        [
            "eval-pdf",
            "--gold-dir",
            str(gold_dir),
            "--pdf-dir",
            str(pdf_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Gold set: 1 annotations loaded" in result.output
    assert "PDF Parser Evaluation Report" in result.output
    assert "Department recall: 1/1 (100.0%)" in result.output
    assert "To run evaluation" not in result.output
