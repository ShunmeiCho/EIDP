"""Import operator-provided external extraction outputs for double-checking.

Goal 4 consumes CSV/XLSX files that users export from Copilot, NotebookLM, or
another manual second-opinion process. It normalizes those files into metric
rows and never uploads PDFs or calls external services.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

__all__ = [
    "EXTERNAL_METRICS",
    "ExternalExtractionImportError",
    "ExternalExtractionRow",
    "ExternalSourceSystem",
    "load_external_extraction_csv",
    "load_external_extraction_file",
    "load_external_extraction_xlsx",
    "normalize_external_extraction_rows",
]


class ExternalExtractionImportError(ValueError):
    """Raised when an external extraction file cannot be normalized."""


class ExternalSourceSystem(StrEnum):
    COPILOT = "copilot"
    NOTEBOOKLM = "notebooklm"
    MANUAL_EXTERNAL = "manual_external"


EXTERNAL_METRICS: tuple[str, ...] = (
    "capacity",
    "enrollment",
    "intl_students",
    "graduates",
    "dropouts",
    "dropout_rate",
)

_HEADER_ALIASES: dict[str, str] = {
    "学校名": "school_name",
    "school": "school_name",
    "schoolname": "school_name",
    "学校id": "school_id",
    "schoolid": "school_id",
    "法人名": "corporation_name",
    "corporation": "corporation_name",
    "corporationname": "corporation_name",
    "都道府県": "prefecture",
    "pref": "prefecture",
    "分野": "field_category",
    "課程名": "field_category",
    "field": "field_category",
    "fieldcategory": "field_category",
    "コース": "course_name",
    "コース名": "course_name",
    "course": "course_name",
    "coursename": "course_name",
    "学科名": "department_name",
    "department": "department_name",
    "departmentname": "department_name",
    "年度": "fiscal_year",
    "fiscalyear": "fiscal_year",
    "year": "fiscal_year",
    "指標": "metric",
    "項目": "metric",
    "metricname": "metric",
    "値": "value",
    "数値": "value",
    "metricvalue": "value",
    "備考": "notes",
    "note": "notes",
    "notes": "notes",
}

_METRIC_ALIASES: dict[str, str] = {
    "収定": "capacity",
    "収容定員": "capacity",
    "定員": "capacity",
    "capacity": "capacity",
    "在籍": "enrollment",
    "在学者数": "enrollment",
    "在籍者数": "enrollment",
    "enrollment": "enrollment",
    "留学生": "intl_students",
    "留学生数": "intl_students",
    "internationalstudents": "intl_students",
    "intlstudents": "intl_students",
    "intl_students": "intl_students",
    "卒業": "graduates",
    "卒業者数": "graduates",
    "graduates": "graduates",
    "中退": "dropouts",
    "中退者数": "dropouts",
    "dropouts": "dropouts",
    "中退率": "dropout_rate",
    "dropoutrate": "dropout_rate",
    "dropout_rate": "dropout_rate",
}


@dataclass(frozen=True)
class ExternalExtractionRow:
    school_name: str
    school_id: str | None
    corporation_name: str | None
    prefecture: str | None
    field_category: str | None
    course_name: str | None
    department_name: str
    fiscal_year: int
    metric: str
    value: int | float | str | None
    source_system: ExternalSourceSystem
    source_file: str
    source_row_number: int
    notes: str | None = None


def load_external_extraction_file(
    file_content: bytes,
    *,
    filename: str,
    source_system: ExternalSourceSystem | str,
) -> list[ExternalExtractionRow]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return load_external_extraction_csv(
            file_content,
            source_system=source_system,
            source_file=filename,
        )
    if suffix in {".xlsx", ".xlsm"}:
        return load_external_extraction_xlsx(
            file_content,
            source_system=source_system,
            source_file=filename,
        )
    raise ExternalExtractionImportError(f"Unsupported external extraction file type: {suffix or '<none>'}")


def load_external_extraction_csv(
    source: Path | str | bytes,
    *,
    source_system: ExternalSourceSystem | str,
    source_file: str | None = None,
) -> list[ExternalExtractionRow]:
    if isinstance(source, bytes):
        text = _decode_csv_bytes(source)
        resolved_source_file = source_file or "external.csv"
    else:
        path = Path(source)
        text = path.read_text(encoding="utf-8-sig")
        resolved_source_file = source_file or path.name
    reader = csv.DictReader(io.StringIO(text))
    return normalize_external_extraction_rows(
        ((row, row_number) for row_number, row in enumerate(reader, start=2)),
        source_system=source_system,
        source_file=resolved_source_file,
    )


def load_external_extraction_xlsx(
    source: Path | str | bytes,
    *,
    source_system: ExternalSourceSystem | str,
    source_file: str | None = None,
    sheet_name: str | None = None,
) -> list[ExternalExtractionRow]:
    import openpyxl  # type: ignore[import-untyped]  # noqa: PLC0415

    if isinstance(source, bytes):
        workbook_source: str | io.BytesIO = io.BytesIO(source)
        resolved_source_file = source_file or "external.xlsx"
    else:
        path = Path(source)
        workbook_source = str(path)
        resolved_source_file = source_file or path.name

    workbook = openpyxl.load_workbook(workbook_source, read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet_name] if sheet_name else workbook.active
        rows_iter = worksheet.iter_rows(values_only=True)
        try:
            headers = next(rows_iter)
        except StopIteration:
            return []
        normalized_headers = [_canonical_header(cell) for cell in headers]
        row_mappings: list[tuple[dict[str, object], int]] = []
        for row_number, row_values in enumerate(rows_iter, start=2):
            row_mappings.append((dict(zip(normalized_headers, row_values, strict=False)), row_number))
        return normalize_external_extraction_rows(
            row_mappings,
            source_system=source_system,
            source_file=resolved_source_file,
        )
    finally:
        workbook.close()


def normalize_external_extraction_rows(
    rows: Iterable[tuple[Mapping[str, object], int]],
    *,
    source_system: ExternalSourceSystem | str,
    source_file: str,
) -> list[ExternalExtractionRow]:
    resolved_source_system = ExternalSourceSystem(source_system)
    normalized: list[ExternalExtractionRow] = []
    for raw_row, row_number in rows:
        canonical = _canonical_row(raw_row)
        if not any(_has_value(value) for value in canonical.values()):
            continue
        normalized.extend(
            _rows_from_canonical_mapping(
                canonical,
                row_number=row_number,
                source_system=resolved_source_system,
                source_file=source_file,
            )
        )
    return normalized


def _rows_from_canonical_mapping(
    row: Mapping[str, object],
    *,
    row_number: int,
    source_system: ExternalSourceSystem,
    source_file: str,
) -> list[ExternalExtractionRow]:
    school_name = _required_text(row, "school_name", row_number)
    department_name = _required_text(row, "department_name", row_number)
    fiscal_year = _required_int(row, "fiscal_year", row_number)
    school_id = _optional_text(row.get("school_id"))
    corporation_name = _optional_text(row.get("corporation_name"))
    prefecture = _optional_text(row.get("prefecture"))
    field_category = _optional_text(row.get("field_category"))
    course_name = _optional_text(row.get("course_name"))
    notes = _optional_text(row.get("notes"))

    explicit_metric = _metric_name(row.get("metric"))
    if explicit_metric:
        return [
            ExternalExtractionRow(
                school_name=school_name,
                school_id=school_id,
                corporation_name=corporation_name,
                prefecture=prefecture,
                field_category=field_category,
                course_name=course_name,
                department_name=department_name,
                fiscal_year=fiscal_year,
                metric=explicit_metric,
                value=_normalize_value(row.get("value")),
                source_system=source_system,
                source_file=source_file,
                source_row_number=row_number,
                notes=notes,
            )
        ]

    metric_rows: list[ExternalExtractionRow] = []
    for metric in EXTERNAL_METRICS:
        value = _normalize_value(row.get(metric))
        if value is not None:
            metric_rows.append(
                ExternalExtractionRow(
                    school_name=school_name,
                    school_id=school_id,
                    corporation_name=corporation_name,
                    prefecture=prefecture,
                    field_category=field_category,
                    course_name=course_name,
                    department_name=department_name,
                    fiscal_year=fiscal_year,
                    metric=metric,
                    value=value,
                    source_system=source_system,
                    source_file=source_file,
                    source_row_number=row_number,
                    notes=notes,
                )
            )
    return metric_rows


def _canonical_row(row: Mapping[str, object]) -> dict[str, object]:
    canonical: dict[str, object] = {}
    for key, value in row.items():
        canonical[_canonical_header(key)] = value
    return canonical


def _canonical_header(value: object) -> str:
    text = _header_key(value)
    return _HEADER_ALIASES.get(text, _METRIC_ALIASES.get(text, text))


def _metric_name(value: object) -> str | None:
    if not _has_value(value):
        return None
    text = _header_key(value)
    metric = _METRIC_ALIASES.get(text, text)
    if metric not in EXTERNAL_METRICS:
        raise ExternalExtractionImportError(f"Unsupported metric: {value}")
    return metric


def _required_text(row: Mapping[str, object], field: str, row_number: int) -> str:
    value = _optional_text(row.get(field))
    if value is None:
        raise ExternalExtractionImportError(f"Row {row_number} is missing required column: {field}")
    return value


def _required_int(row: Mapping[str, object], field: str, row_number: int) -> int:
    value = row.get(field)
    if isinstance(value, bool):
        raise ExternalExtractionImportError(f"Row {row_number} has invalid {field}: {value}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = _optional_text(value)
    if text is None:
        raise ExternalExtractionImportError(f"Row {row_number} is missing required column: {field}")
    try:
        return int(float(text.replace(",", "")))
    except ValueError as exc:
        raise ExternalExtractionImportError(f"Row {row_number} has invalid {field}: {text}") from exc


def _normalize_value(value: object) -> int | float | str | None:
    if not _has_value(value):
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    text = str(value).strip()
    number_text = text.replace(",", "")
    try:
        number = float(number_text)
    except ValueError:
        return text
    return int(number) if number.is_integer() else number


def _optional_text(value: object) -> str | None:
    if not _has_value(value):
        return None
    text = str(value).strip()
    return text or None


def _has_value(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text not in {"", "-", "‐", "―"}


def _header_key(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "").replace("_", "")


def _decode_csv_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp932")
