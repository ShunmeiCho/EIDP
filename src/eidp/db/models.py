"""SQLAlchemy ORM models — 12 tables per design doc Section 4."""

from datetime import datetime

from sqlalchemy import (
    DDL,
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("prefecture", "corporation_name", "school_name", name="uq_school_natural_key"),
        {"comment": "School identity table"},
    )

    sites: Mapped[list["SchoolSite"]] = relationship(back_populates="school")
    departments: Mapped[list["Department"]] = relationship(back_populates="school")
    year_statuses: Mapped[list["SchoolYearStatus"]] = relationship(back_populates="school")
    fiscal_year_statuses: Mapped[list["SchoolFiscalYearStatus"]] = relationship(back_populates="school")
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
        Index("idx_school_site_school_id_http_status", "school_id", "http_status"),
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
    fiscal_year_override: Mapped[int | None] = mapped_column(Integer)
    is_current_year: Mapped[bool | None] = mapped_column(Boolean)
    content_type: Mapped[str | None] = mapped_column(String(20))
    pdf_type: Mapped[str | None] = mapped_column(String(30))  # target, non_target, image_only, unknown
    ingest_status: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("school_id", "file_hash"),
        UniqueConstraint("school_id", "source_url", name="uq_document_school_url"),
        # pdf_discovery looks up by file_hash alone and treats cross-school
        # matches as operator-review duplicates. Keep the database contract
        # aligned with that probe so concurrent workers cannot attach the same
        # PDF bytes to multiple schools.
        Index("uq_document_file_hash", "file_hash", unique=True),
        Index("idx_document_school_id", "school_id"),
        Index("idx_document_fiscal_year_pdf_type_ingest_status", "fiscal_year", "pdf_type", "ingest_status"),
        {"comment": "PDF document registry"},
    )


class Department(Base):
    __tablename__ = "department"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    course_name: Mapped[str | None] = mapped_column(String(200))  # 課程名
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    course_type: Mapped[str | None] = mapped_column(String(10))
    duration_years: Mapped[float | None] = mapped_column(Numeric(3, 1))
    field_category: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "school_id", "canonical_name", "course_type", "course_name", "duration_years",
            name="uq_department_natural_key",
        ),
        {"comment": "Department identity table"},
    )

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
    voided: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by: Mapped[str | None] = mapped_column(String(50))
    void_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_department_change_department_id", "department_id"),
    )

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
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    extraction_method: Mapped[str | None] = mapped_column(String(20))
    confidence_breakdown: Mapped[str | None] = mapped_column(Text)
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
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        Index("idx_department_yearly_document_id", "document_id"),
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

    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("school_id", "fiscal_year", "revision", name="uq_school_year_status_revision"),
        Index(
            "idx_school_year_status_current",
            "school_id",
            "fiscal_year",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        {"comment": "School-year collection status tracking (append-only with revision support)"},
    )

    school: Mapped["School"] = relationship(back_populates="year_statuses")


class SchoolFiscalYearStatus(Base):
    """Operator-facing School x target fiscal year progress row.

    This denormalized table is rebuilt from source-of-truth tables so the UI can
    show one task row per school instead of making operators reason from a raw
    document queue.
    """

    __tablename__ = "school_fiscal_year_status"

    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), primary_key=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, primary_key=True)
    url_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    pdf_status: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    extract_status: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    yoy_diff_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unchecked")
    excel_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocking_reason: Mapped[str | None] = mapped_column(Text)
    evidence_level: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_school_fy_status_fy_pdf", "fiscal_year", "pdf_status"),
        Index("idx_school_fy_status_fy_ready", "fiscal_year", "excel_ready"),
        {"comment": "Denormalized School x fiscal-year operator task status"},
    )

    school: Mapped["School"] = relationship(back_populates="fiscal_year_statuses")


class SchoolAlias(Base):
    __tablename__ = "school_alias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    alias_name: Mapped[str] = mapped_column(String(200), nullable=False)
    alias_type: Mapped[str | None] = mapped_column(String(30))
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_school_alias_school_id", "school_id"),
    )

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
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    confidence_breakdown: Mapped[str | None] = mapped_column(Text)  # 8.2.c: JSON, mirrors DepartmentYearly
    notes: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("school_id", "fiscal_year", "revision", name="uq_support_recipient_revision"),
        Index(
            "idx_support_recipient_current",
            "school_id",
            "fiscal_year",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        {"comment": "Support recipient data for 対象比率 sheet (append-only with revision support)"},
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


class ManualActionLog(Base):
    """Audit log for business-user actions (Sprint 8.2.c).

    DB is the authoritative source. ``data/audit/manual-actions.jsonl`` is an
    after-commit outbox that is rebuilt from this table on demand. ``action_id``
    is a stable UUID assigned at insert so the JSONL outbox can dedup against
    the DB rows.
    """

    __tablename__ = "manual_action_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)  # UUID4
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actor: Mapped[str] = mapped_column(String(50), nullable=False, default="operator")
    identity_source: Mapped[str | None] = mapped_column(String(32))
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_table: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))
    old_value: Mapped[str | None] = mapped_column(Text)  # JSON
    new_value: Mapped[str | None] = mapped_column(Text)  # JSON
    reason: Mapped[str | None] = mapped_column(Text)
    jsonl_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jsonl_export_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index(
            "idx_manual_action_log_jsonl_exported_table_document",
            "jsonl_exported_at",
            "target_table",
            "document_id",
        ),
    )


class ExtractionReviewDecision(Base):
    """Append-only authoritative decision for one immutable extraction review record."""

    __tablename__ = "extraction_review_decision"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    review_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    corrected_value: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    identity_source: Mapped[str] = mapped_column(String(32), nullable=False)
    audit_action_id: Mapped[str] = mapped_column(
        ForeignKey("manual_action_log.action_id"),
        unique=True,
        nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "review_id",
            "revision",
            name="uq_extraction_review_decision_review_revision",
        ),
        Index(
            "uq_extraction_review_decision_provenance",
            "review_id",
            "revision",
            "audit_action_id",
            unique=True,
        ),
        CheckConstraint(
            "decision != 'exclude' OR "
            "length(trim(coalesce(note, ''))) BETWEEN 1 AND 500",
            name="ck_extraction_review_decision_exclude_reason",
        ),
        {"comment": "Append-only audited extraction review decisions"},
    )


class ExternalComparisonRun(Base):
    """One immutable comparison of reviewed EIDP rows to an external file."""

    __tablename__ = "external_comparison_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_system: Mapped[str] = mapped_column(String(32), nullable=False)
    external_file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    external_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    report_path: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    identity_source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("run_id", name="uq_external_comparison_run_run_id"),
        UniqueConstraint(
            "run_id",
            "external_file_sha256",
            name="uq_external_comparison_run_run_hash",
        ),
        CheckConstraint(
            "source_system IN ('copilot', 'notebooklm', 'manual_external')",
            name="ck_external_comparison_run_source_system",
        ),
        CheckConstraint(
            "length(external_file_sha256) = 64",
            name="ck_external_comparison_run_file_sha256",
        ),
        CheckConstraint(
            "length(report_sha256) = 64",
            name="ck_external_comparison_run_report_sha256",
        ),
        Index("ix_external_comparison_run_external_file_sha256", "external_file_sha256"),
        {"comment": "Immutable external comparison run and content-addressed artifacts"},
    )


class ExternalComparisonResult(Base):
    """Immutable snapshot of one row emitted by an external comparison run."""

    __tablename__ = "external_comparison_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("external_comparison_run.run_id"), nullable=False)
    row_key: Mapped[str] = mapped_column(String(64), nullable=False)
    comparison_key: Mapped[str] = mapped_column(Text, nullable=False)
    review_id: Mapped[str | None] = mapped_column(String(80))
    review_decision_revision: Mapped[int | None] = mapped_column(Integer)
    review_audit_action_id: Mapped[str | None] = mapped_column(String(36))
    external_source_row_key: Mapped[str | None] = mapped_column(Text)
    external_value: Mapped[int | float | str | None] = mapped_column(JSON(none_as_null=True))
    external_file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    eidp_value: Mapped[int | float | str | None] = mapped_column(JSON(none_as_null=True))
    comparison_status: Mapped[str] = mapped_column(String(48), nullable=False)
    mismatch_reason: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "row_key",
            name="uq_external_comparison_result_run_row",
        ),
        CheckConstraint(
            "comparison_status IN ("
            "'match', 'value_mismatch', 'missing_in_eidp', 'missing_in_external', "
            "'ambiguous_key_not_comparable', 'needs_review_not_comparable', "
            "'excluded_not_comparable')",
            name="ck_external_comparison_result_status",
        ),
        CheckConstraint(
            "length(external_file_sha256) = 64",
            name="ck_external_comparison_result_file_sha256",
        ),
        CheckConstraint(
            "review_decision_revision IS NULL OR review_decision_revision >= 1",
            name="ck_external_comparison_result_review_revision",
        ),
        CheckConstraint(
            "(review_decision_revision IS NULL AND review_audit_action_id IS NULL) OR "
            "(review_id IS NOT NULL AND review_decision_revision IS NOT NULL "
            "AND review_audit_action_id IS NOT NULL)",
            name="ck_external_comparison_result_review_provenance",
        ),
        ForeignKeyConstraint(
            ["run_id", "external_file_sha256"],
            [
                "external_comparison_run.run_id",
                "external_comparison_run.external_file_sha256",
            ],
            name="fk_external_comparison_result_run_hash",
        ),
        ForeignKeyConstraint(
            ["review_id", "review_decision_revision", "review_audit_action_id"],
            [
                "extraction_review_decision.review_id",
                "extraction_review_decision.revision",
                "extraction_review_decision.audit_action_id",
            ],
            name="fk_external_comparison_result_review_provenance",
        ),
        {"comment": "Immutable per-row external comparison snapshot"},
    )


class DoubleCheckResolution(Base):
    """Append-only audited human resolution of one comparison result snapshot."""

    __tablename__ = "double_check_resolution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resolution_id: Mapped[str] = mapped_column(String(36), nullable=False)
    comparison_result_id: Mapped[int] = mapped_column(
        ForeignKey("external_comparison_result.id"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    corrected_value: Mapped[int | None] = mapped_column(Integer)
    effective_value: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    identity_source: Mapped[str] = mapped_column(String(32), nullable=False)
    audit_action_id: Mapped[str] = mapped_column(
        ForeignKey("manual_action_log.action_id"),
        nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("resolution_id", name="uq_double_check_resolution_resolution_id"),
        UniqueConstraint("audit_action_id", name="uq_double_check_resolution_audit_action_id"),
        UniqueConstraint(
            "comparison_result_id",
            "revision",
            name="uq_double_check_resolution_result_revision",
        ),
        CheckConstraint("revision >= 1", name="ck_double_check_resolution_revision"),
        CheckConstraint(
            "outcome IN ('accept_eidp', 'accept_external', 'correct', 'exclude')",
            name="ck_double_check_resolution_outcome",
        ),
        CheckConstraint(
            "length(trim(coalesce(reason, ''))) BETWEEN 1 AND 500",
            name="ck_double_check_resolution_reason",
        ),
        CheckConstraint(
            "(outcome = 'accept_eidp' AND corrected_value IS NULL AND effective_value IS NOT NULL) OR "
            "(outcome = 'accept_external' AND corrected_value IS NOT NULL "
            "AND effective_value = corrected_value) OR "
            "(outcome = 'correct' AND corrected_value IS NOT NULL AND corrected_value >= 0 "
            "AND effective_value = corrected_value) OR "
            "(outcome = 'exclude' AND corrected_value IS NULL AND effective_value IS NULL)",
            name="ck_double_check_resolution_value_contract",
        ),
        {"comment": "Append-only audited double-check resolutions"},
    )


_TASK5_IMMUTABLE_MODELS = (
    ExternalComparisonRun,
    ExternalComparisonResult,
    DoubleCheckResolution,
)

for _immutable_model in _TASK5_IMMUTABLE_MODELS:
    for _operation in ("UPDATE", "DELETE"):
        _table_name = _immutable_model.__tablename__
        _trigger_name = f"trg_{_table_name}_immutable_{_operation.lower()}"
        event.listen(
            _immutable_model.__table__,
            "after_create",
            DDL(  # type: ignore[no-untyped-call]  # SQLAlchemy ships this callable untyped
                f"""
                CREATE TRIGGER IF NOT EXISTS {_trigger_name}
                BEFORE {_operation} ON {_table_name}
                BEGIN
                    SELECT RAISE(ABORT, '{_table_name} is immutable');
                END
                """
            ).execute_if(dialect="sqlite"),
        )
