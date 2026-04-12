"""Gold set annotation schema for PDF parser evaluation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DepartmentRecord(BaseModel):
    """Per-department enrollment data extracted from Form 2-4-2 section."""

    name: str = Field(description="Department name (学科名)")
    course_name: str | None = Field(default=None, description="Course/program name (課程名)")
    duration_years: float | None = Field(default=None, description="Program duration in years (supports 1.5, 2.4 etc.)")
    day_or_evening: str | None = Field(default=None, description="Day or evening (昼/夜)")
    capacity: int | None = Field(default=None, description="Student capacity (収定)")
    enrollment: int | None = Field(default=None, description="Enrolled students (在籍)")
    intl_students: int | None = Field(default=0, description="International students (留学生)")
    graduates: int | None = Field(default=None, description="Graduates (卒業)")
    advanced: int | None = Field(default=0, description="Advanced to higher ed (進学)")
    employed: int | None = Field(default=None, description="Employed (就職)")
    other: int | None = Field(default=0, description="Other outcomes")
    prev_enrollment: int | None = Field(default=0, description="Previous year enrollment (前年在籍)")
    dropouts: int | None = Field(default=0, description="Dropouts (中退)")
    dropout_rate: float | None = Field(default=0.0, description="Dropout rate % (中退率)")


class SchoolAnnotation(BaseModel):
    """Complete annotation for one school's PDF."""

    school_name: str = Field(default="", description="School name")
    school_type: str = Field(default="専門学校")
    operator_name: str = Field(default="")
    fiscal_year: str = Field(default="")
    source_pdf: str = Field(default="")
    departments: list[DepartmentRecord] = Field(default_factory=list)
