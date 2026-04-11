"""Gold set annotation schema for PDF parser evaluation.

Defines the expected output structure for parsed enrollment data
from MEXT institutional confirmation application PDFs
(高等教育の修学支援新制度 機関要件確認申請書).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DepartmentRecord(BaseModel):
    """Per-department enrollment data extracted from Form 2-4-2 section."""

    name: str = Field(description="Department name (学科名)")
    course_name: str = Field(
        default="",
        description="Course/program name (課程名), e.g. 工業専門課程",
    )
    duration_years: int = Field(
        description="Program duration in years (修業年限)",
    )
    day_or_evening: str = Field(
        default="昼",
        description="Day or evening program (昼/夜)",
    )
    capacity: int = Field(
        description="Total student capacity (生徒総定員数)",
    )
    enrollment: int = Field(
        description="Actual enrolled students (生徒実員)",
    )
    intl_students: int = Field(
        default=0,
        description="International students (うち留学生数)",
    )
    graduates: int = Field(
        description="Number of graduates (卒業者数)",
    )
    advanced: int = Field(
        default=0,
        description="Graduates who advanced to further study (進学者数)",
    )
    employed: int = Field(
        description="Graduates who got employed (就職者数)",
    )
    other: int = Field(
        default=0,
        description="Other outcomes (その他)",
    )
    prev_enrollment: int = Field(
        default=0,
        description="Enrollment at beginning of fiscal year (年度当初在学者数)",
    )
    dropouts: int = Field(
        default=0,
        description="Number of dropouts during fiscal year (年度の途中における退学者の数)",
    )
    dropout_rate: float = Field(
        default=0.0,
        description="Dropout rate percentage (中退率 %)",
    )


class SchoolAnnotation(BaseModel):
    """Complete annotation for one school's PDF.

    Contains school-level metadata and all department records
    extracted from the PDF.
    """

    school_name: str = Field(
        description="Official school name (学校名)",
    )
    school_type: str = Field(
        default="専門学校",
        description="Type of institution (大学/短期大学/高等専門学校/専門学校)",
    )
    operator_name: str = Field(
        default="",
        description="Operating entity name (設置者の名称)",
    )
    fiscal_year: str = Field(
        description="Fiscal year of the application (e.g. 令和7年度)",
    )
    source_pdf: str = Field(
        description="Source PDF filename",
    )
    departments: list[DepartmentRecord] = Field(
        default_factory=list,
        description="List of department enrollment records",
    )
