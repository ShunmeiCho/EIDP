"""Sprint 8.6.c — Tesseract subprocess wrapper.

Wraps the system / add-on Tesseract binary, parses its TSV output, and
returns a structured ``OcrPageResult``. Sprint 8.6.d will plug
``compute_f1_ocr_tesseract`` into the per-page result so the confidence
breakdown surfaces alongside ``DepartmentYearly`` rows.

Layout assumptions on Windows operator PC (set by the OCR add-on ZIP):

    %EIDP_APP_ROOT%\\ocr-addon\\tesseract\\tesseract.exe
    %EIDP_APP_ROOT%\\ocr-addon\\tessdata\\jpn.traineddata

On dev / Linux / macOS the binary may live on PATH (``which
tesseract``) or under the operator add-on directory; ``locate_tesseract``
prefers the add-on path when available so dev-host quirks don't bleed
into operator PC behavior.

The module is designed to be unit-testable without invoking a real
Tesseract — every subprocess hop is funneled through a single
``runner`` callable that tests can stub.
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class OcrError(RuntimeError):
    """Generic Tesseract failure (non-zero exit, malformed TSV, etc.)."""


class OcrBinaryNotFoundError(OcrError):
    """Raised when ``locate_tesseract`` cannot find a usable binary."""


@dataclass(frozen=True)
class OcrWord:
    """One token row from Tesseract TSV output.

    ``conf`` is the per-word confidence as Tesseract reports it: 0..100
    for usable tokens, ``-1`` for tokens it could not recognize. The
    sentinel is preserved so ``compute_f1_ocr_tesseract`` can drop it
    when computing the mean confidence (per Sprint 8.6.a contract).
    """

    text: str
    conf: int
    line_num: int
    word_num: int
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class OcrPageResult:
    """Aggregated TSV result for one page."""

    words: list[OcrWord]
    full_text: str

    @property
    def conf_values(self) -> list[int]:
        """Just the conf column — the only thing
        ``compute_f1_ocr_tesseract`` needs."""
        return [w.conf for w in self.words]

    @property
    def usable_words(self) -> list[OcrWord]:
        return [w for w in self.words if w.conf >= 0 and w.text.strip()]


# ---------------------------------------------------------------------------
# Binary location
# ---------------------------------------------------------------------------


def locate_tesseract(*, app_root: Path | None = None,
                      env: dict[str, str] | None = None) -> Path:
    """Find a usable ``tesseract`` binary.

    Resolution order, first match wins:

    1. ``EIDP_TESSERACT_BIN`` env var (operator override).
    2. ``app_root / "ocr-addon" / "tesseract" / "tesseract.exe"`` (Windows
       add-on layout) or ``.../tesseract`` (POSIX dev) — the canonical
       path the OCR add-on ZIP populates.
    3. ``shutil.which("tesseract")`` — system PATH fallback for dev.

    Raises ``OcrBinaryNotFoundError`` with a single readable message if
    none of the above resolve. We surface a clean exception rather than
    falling back to ``None`` so callers can render a deterministic UI
    banner ("OCR add-on not installed").
    """
    env_map = env if env is not None else os.environ

    explicit = env_map.get("EIDP_TESSERACT_BIN")
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return candidate
        raise OcrBinaryNotFoundError(
            f"EIDP_TESSERACT_BIN points at {candidate}, which does not exist"
        )

    if app_root is not None:
        for relative in (
            Path("ocr-addon") / "tesseract" / "tesseract.exe",
            Path("ocr-addon") / "tesseract" / "tesseract",
        ):
            candidate = app_root / relative
            if candidate.is_file():
                return candidate

    on_path = shutil.which("tesseract")
    if on_path:
        return Path(on_path)

    raise OcrBinaryNotFoundError(
        "tesseract binary not found — install OCR add-on or set "
        "EIDP_TESSERACT_BIN to an absolute path"
    )


def locate_tessdata(*, app_root: Path | None = None,
                     env: dict[str, str] | None = None) -> Path | None:
    """Find the directory containing ``jpn.traineddata``. Returns
    ``None`` when no candidate exists; callers may proceed in
    English-only mode or surface a UI warning."""
    env_map = env if env is not None else os.environ

    explicit = env_map.get("TESSDATA_PREFIX")
    if explicit:
        candidate = Path(explicit).expanduser()
        if (candidate / "jpn.traineddata").is_file():
            return candidate
        if candidate.is_dir():
            return candidate

    if app_root is not None:
        candidate = app_root / "ocr-addon" / "tessdata"
        if candidate.is_dir():
            return candidate

    return None


# ---------------------------------------------------------------------------
# TSV parsing
# ---------------------------------------------------------------------------


_REQUIRED_TSV_COLUMNS = (
    "level", "page_num", "block_num", "par_num",
    "line_num", "word_num", "left", "top", "width", "height",
    "conf", "text",
)


def parse_tesseract_tsv(tsv_text: str) -> OcrPageResult:
    """Convert Tesseract TSV stdout into a structured page result.

    Tesseract prints a header row followed by one row per detected
    bounding box. Word rows are level == 5; line / paragraph / block
    rows have empty text. We only keep word rows and treat empty-text
    word rows (level==5 conf==-1) as "no token recognized" — these get
    a conf of -1 in the result so callers can drop them.
    """
    if not tsv_text.strip():
        return OcrPageResult(words=[], full_text="")

    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    if reader.fieldnames is None:
        raise OcrError("tesseract TSV has no header row")
    missing = [c for c in _REQUIRED_TSV_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise OcrError(f"tesseract TSV missing columns: {missing}")

    words: list[OcrWord] = []
    text_lines: dict[int, list[str]] = {}
    for row in reader:
        try:
            level = int(row["level"])
        except (TypeError, ValueError):
            continue
        if level != 5:
            continue  # skip block/paragraph/line aggregations
        text = (row.get("text") or "").strip()
        try:
            conf = int(float(row.get("conf", "-1")))
        except (TypeError, ValueError):
            conf = -1

        try:
            line_num = int(row.get("line_num") or 0)
            word_num = int(row.get("word_num") or 0)
            left = int(row.get("left") or 0)
            top = int(row.get("top") or 0)
            width = int(row.get("width") or 0)
            height = int(row.get("height") or 0)
        except (TypeError, ValueError):
            # Bad numeric cell — drop the row rather than crash. OCR
            # noise should never take down ingest.
            continue

        words.append(OcrWord(
            text=text, conf=conf,
            line_num=line_num, word_num=word_num,
            left=left, top=top, width=width, height=height,
        ))
        if text:
            text_lines.setdefault(line_num, []).append(text)

    full_text = "\n".join(
        " ".join(text_lines[k]) for k in sorted(text_lines)
    )
    return OcrPageResult(words=words, full_text=full_text)


# ---------------------------------------------------------------------------
# Subprocess hop
# ---------------------------------------------------------------------------


# Type alias for the subprocess seam used by tests.
RunnerResult = subprocess.CompletedProcess[str]
Runner = Callable[[list[str]], RunnerResult]


def _default_runner(cmd: list[str]) -> RunnerResult:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def run_tesseract_on_image(
    image_path: Path,
    *,
    binary: Path | None = None,
    tessdata_dir: Path | None = None,
    lang: str = "jpn+eng",
    psm: int = 6,
    runner: Runner = _default_runner,
) -> OcrPageResult:
    """Run Tesseract on a single PNG/TIF and parse the TSV.

    ``runner`` is the subprocess seam — tests pass a stub that returns a
    ``CompletedProcess`` with hand-crafted ``stdout``. Production
    callers leave it at the default which shells out to the bundled
    binary.

    ``psm=6`` ("Assume a single uniform block of text") is the Tesseract
    page-segmentation mode that works best on the table-heavy form
    layouts EIDP ingests; callers can override per page. ``lang`` is
    ``jpn+eng`` because the disclosure forms have Japanese labels and
    Latin numerals.
    """
    if not image_path.is_file():
        raise OcrError(f"OCR input image does not exist: {image_path}")

    cmd: list[str] = [
        str(binary) if binary else "tesseract",
        str(image_path),
        "stdout",
        "-l", lang,
        "--psm", str(psm),
        "tsv",
    ]
    if tessdata_dir is not None:
        cmd[1:1] = ["--tessdata-dir", str(tessdata_dir)]

    completed = runner(cmd)
    if completed.returncode != 0:
        raise OcrError(
            f"tesseract exited rc={completed.returncode}: "
            f"{(completed.stderr or '').strip()[:400]}"
        )
    return parse_tesseract_tsv(completed.stdout or "")
