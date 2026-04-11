"""SQLAlchemy ORM models — 12 tables per design doc Section 4."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = "school"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_code: Mapped[str | None] = mapped_column(String(20), unique=True)
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    corporation_name: Mapped[str] = mapped_column(String(200), nullable=False)
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)
    school_type: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sites: Mapped[list["SchoolSite"]] = relationship(back_populates="school")
    departments: Mapped[list["Department"]] = relationship(back_populates="school")
    year_statuses: Mapped[list["SchoolYearStatus"]] = relationship(back_populates="school")
    aliases: Mapped[list["SchoolAlias"]] = relationship(back_populates="school")
    support_recipients: Mapped[list["SupportRecipient"]] = relationship(back_populates="school")


class SchoolSite(Base):
    __tablename__ = "school_site"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_type: Mapped[str | None] = mapped_column(String(30))
    discovery_method: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("school_id", "url"),
        {"comment": "School website registry"},
    )

    school: Mapped["School"] = relationship(back_populates="sites")


class CrawlJob(Base):
    __tablename__ = "crawl_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    job_type: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    discovered_from: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(Text)
    file_hash: Mapped[str | None] = mapped_column(String(64))
    file_size: Mapped[int | None] = mapped_column(Integer)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    is_current_year: Mapped[bool | None] = mapped_column(Boolean)
    content_type: Mapped[str | None] = mapped_column(String(20))
    pdf_type: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("school_id", "file_hash"),
        {"comment": "PDF document registry"},
    )


class Department(Base):
    __tablename__ = "department"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    course_name: Mapped[str | None] = mapped_column(String(200))  # 課程名
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    course_type: Mapped[str | None] = mapped_column(String(10))
    duration_years: Mapped[int | None] = mapped_column(Integer)
    field_category: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    school: Mapped["School"] = relationship(back_populates="departments")
    yearly_data: Mapped[list["DepartmentYearly"]] = relationship(back_populates="department")
    changes: Mapped[list["DepartmentChange"]] = relationship(
        back_populates="department", foreign_keys="DepartmentChange.department_id"
    )


class DepartmentChange(Base):
    __tablename__ = "department_change"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    old_name: Mapped[str | None] = mapped_column(String(200))
    new_name: Mapped[str | None] = mapped_column(String(200))
    related_dept_id: Mapped[int | None] = mapped_column(ForeignKey("department.id"))
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

    department: Mapped["Department"] = relationship(
        back_populates="changes", foreign_keys=[department_id]
    )


class DepartmentYearly(Base):
    __tablename__ = "department_yearly"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), nullable=False)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    capacity: Mapped[int | None] = mapped_column(Integer)
    enrollment: Mapped[int | None] = mapped_column(Integer)
    intl_students: Mapped[int | None] = mapped_column(Integer)
    graduates: Mapped[int | None] = mapped_column(Integer)
    advanced: Mapped[int | None] = mapped_column(Integer)
    employed: Mapped[int | None] = mapped_column(Integer)
    other: Mapped[int | None] = mapped_column(Integer)
    prev_enrollment: Mapped[int | None] = mapped_column(Integer)
    dropouts: Mapped[int | None] = mapped_column(Integer)
    dropout_rate: Mapped[float | None] = mapped_column(Numeric(7, 4))
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    extraction_method: Mapped[str | None] = mapped_column(String(20))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("department_id", "fiscal_year", "revision"),
        Index(
            "idx_dept_yearly_current",
            "department_id",
            "fiscal_year",
            unique=True,
            postgresql_where="is_current = true",
        ),
        {"comment": "Yearly department snapshot, append-only with revision support"},
    )

    department: Mapped["Department"] = relationship(back_populates="yearly_data")


class SchoolYearStatus(Base):
    __tablename__ = "school_year_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    legacy_status: Mapped[str | None] = mapped_column(String(50))
    excluded_reason: Mapped[str | None] = mapped_column(String(50))
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("school_id", "fiscal_year"),
        {"comment": "School-year collection status tracking"},
    )

    school: Mapped["School"] = relationship(back_populates="year_statuses")


class SchoolAlias(Base):
    __tablename__ = "school_alias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    alias_name: Mapped[str] = mapped_column(String(200), nullable=False)
    alias_type: Mapped[str | None] = mapped_column(String(30))
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    school: Mapped["School"] = relationship(back_populates="aliases")


class SupportRecipient(Base):
    __tablename__ = "support_recipient"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    school_number: Mapped[str | None] = mapped_column(String(20))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    first_half_total: Mapped[int | None] = mapped_column(Integer)  # 前半期
    first_half_cat1: Mapped[int | None] = mapped_column(Integer)
    first_half_cat2: Mapped[int | None] = mapped_column(Integer)
    first_half_cat3: Mapped[int | None] = mapped_column(Integer)
    first_half_cat4: Mapped[int | None] = mapped_column(Integer)
    second_half_total: Mapped[int | None] = mapped_column(Integer)  # 後半期
    second_half_cat1: Mapped[int | None] = mapped_column(Integer)
    second_half_cat2: Mapped[int | None] = mapped_column(Integer)
    second_half_cat3: Mapped[int | None] = mapped_column(Integer)
    second_half_cat4: Mapped[int | None] = mapped_column(Integer)
    annual_total: Mapped[int | None] = mapped_column(Integer)  # 年間
    household_change: Mapped[int | None] = mapped_column(Integer)  # 家計急変多子世帯
    grand_total: Mapped[int | None] = mapped_column(Integer)  # 総計
    prev_enrollment: Mapped[int | None] = mapped_column(Integer)
    recipient_rate: Mapped[float | None] = mapped_column(Numeric(7, 4))
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("school_id", "fiscal_year"),
        {"comment": "Support recipient data for 対象比率 sheet"},
    )

    school: Mapped["School"] = relationship(back_populates="support_recipients")


class TaxonomyMapping(Base):
    __tablename__ = "taxonomy_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_pattern: Mapped[str] = mapped_column(String(200), nullable=False)
    field_category: Mapped[str] = mapped_column(String(50), nullable=False)
    match_type: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("department_pattern", "field_category"),
        {"comment": "Persisted human decisions for competition classification"},
    )


class ReviewItem(Base):
    __tablename__ = "review_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_type: Mapped[str | None] = mapped_column(String(30))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    reference_table: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=5)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    proposal_value: Mapped[str | None] = mapped_column(Text)  # AI/rule proposed value (JSON)
    proposal_reason: Mapped[str | None] = mapped_column(Text)  # why this was proposed
    proposal_source: Mapped[str | None] = mapped_column(String(50))  # rule, llm, web_search
    evidence_url: Mapped[str | None] = mapped_column(Text)  # supporting evidence link
    assigned_to: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(String(20))  # approved, rejected, corrected
    resolved_value: Mapped[str | None] = mapped_column(Text)  # actual applied value (if corrected)
    notes: Mapped[str | None] = mapped_column(Text)
