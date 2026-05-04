"""Sprint 8.6.d.3 — OCR availability detection for the operator UI.

The PDF確認・手入力 page asks one question on every render: ``can the
operator hit an OCR button right now?``. The answer depends on three
independent things:

1. Is the Tesseract binary present? (``locate_tesseract``)
2. Is the ``jpn.traineddata`` available? (``locate_tessdata`` returning a
   directory that actually contains the file)
3. Did ``ocr_auto_enable`` say the hardware is up to it?

This module bundles the three checks into one ``OcrAvailability``
dataclass plus a UI-friendly banner text helper. Pure logic — no
``streamlit`` imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eidp.ocr.runtime_detect import RuntimeProfile, ocr_auto_enable
from eidp.ocr.tesseract import (
    OcrBinaryNotFoundError,
    locate_tessdata,
    locate_tesseract,
)


@dataclass(frozen=True)
class OcrAvailability:
    """Snapshot of OCR readiness on the operator PC."""

    binary_path: Path | None
    tessdata_dir: Path | None
    has_jpn_traineddata: bool
    auto_enabled: bool

    @property
    def can_run(self) -> bool:
        """True iff the operator can press an OCR button and expect a
        useful result. Requires binary + jpn data; auto_enabled is
        independent — operator can still manually OCR a single PDF on
        a low-spec PC."""
        return self.binary_path is not None and self.has_jpn_traineddata

    @property
    def auto_can_run(self) -> bool:
        """True iff OCR should run automatically during weekly ingest."""
        return self.can_run and self.auto_enabled


def detect_ocr_availability(
    *,
    app_root: Path | None = None,
    env: dict[str, str] | None = None,
    profile: RuntimeProfile | None = None,
) -> OcrAvailability:
    """Bundle binary + tessdata + auto-enable checks into one snapshot."""
    try:
        binary = locate_tesseract(app_root=app_root, env=env)
    except OcrBinaryNotFoundError:
        binary = None

    tessdata = locate_tessdata(app_root=app_root, env=env)
    has_jpn = tessdata is not None and (tessdata / "jpn.traineddata").is_file()

    auto = ocr_auto_enable(profile=profile, env=env)

    return OcrAvailability(
        binary_path=binary,
        tessdata_dir=tessdata,
        has_jpn_traineddata=has_jpn,
        auto_enabled=auto,
    )


def availability_banner_text(detection: OcrAvailability) -> str:
    """One-line operator-facing status. Japanese.

    Wording is tuned for the manual-entry page header — short, factual,
    no emoji (operator setting may not render them on cp932 console).
    """
    if not detection.binary_path:
        return "OCR add-on 未インストール — 画像 PDF は手入力で対応してください。"
    if not detection.has_jpn_traineddata:
        return (
            "Tesseract は導入済みですが jpn.traineddata が見つかりません。"
            " add-on ZIP の再展開を確認してください。"
        )
    if not detection.auto_enabled:
        return (
            "OCR add-on 利用可能。自動実行は OFF（CPU/メモリしきい値未満）— "
            "個別 PDF ボタンで手動 OCR は可能です。"
        )
    return "OCR add-on 利用可能（自動実行 ON）。"


def availability_banner_severity(detection: OcrAvailability) -> str:
    """Map the banner to a Streamlit-style severity bucket: ``error`` /
    ``warning`` / ``info`` / ``success``. The page renders st.error()
    vs st.info() based on this so the operator's eye lands on the
    relevant one first."""
    if not detection.binary_path:
        return "info"  # not having OCR is not an error — it's optional add-on
    if not detection.has_jpn_traineddata:
        return "warning"
    if not detection.auto_enabled:
        return "info"
    return "success"
