"""PDF text extractor — Step 9.

Extracts enrollment data from 機関要件確認申請書 PDFs.
The data is in text lines (not tables): each department section contains:
- 学科名, 課程名, 昼夜, 年限 in the section header
- "生徒総定員数 生徒実員 うち留学生数" header line
- Numeric values on the next line
- "卒業者数 進学者数 就職者数" in a separate table
- "中退者" data in appendix

2-tier: pdfplumber text extraction (Tier 1) -> MinerU/VL-OCR (Tier 2)
"""

import re
import unicodedata
from pathlib import Path

import structlog

from eidp.pdf.schema import DepartmentRecord, SchoolAnnotation

log = structlog.get_logger()


def _norm(text: str | None) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def _extract_ints(text: str) -> list[int]:
    """Extract all integers from a text line."""
    return [int(x) for x in re.findall(r"\d+", text.replace(",", ""))]


def parse_pdf(pdf_path: Path) -> SchoolAnnotation:
    """Parse a 機関要件確認申請書 PDF."""
    import pdfplumber

    departments: list[DepartmentRecord] = []
    school_name = ""
    operator_name = ""
    fiscal_year = ""

    with pdfplumber.open(str(pdf_path)) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n===PAGE===\n"

    # Extract school-level info
    m = re.search(r"令和\d+年度", full_text)
    if m:
        fiscal_year = _norm(m.group(0))

    # Extract school name from "名称" field or title
    m = re.search(r"(?:確認を受けた|学校の)(?:名称|概要).*?名称[：:\s]*(.+?)(?:\n|設置者)", full_text, re.DOTALL)
    if m:
        school_name = _norm(m.group(1).split("\n")[0])

    # Fallback: search for school name pattern
    if not school_name:
        m = re.search(r"(?:専門学校|学院|学園|学校)[\s\S]{0,20}(?:名称)[：:\s]*(.+)", full_text)
        if m:
            school_name = _norm(m.group(1).split("\n")[0])

    # Extract per-department data
    # Pattern: each department page has:
    # 1. 学科名 in the header table
    # 2. "生徒総定員数 生徒実員 うち留学生数" followed by numbers
    # 3. "卒業者数 進学者数 就職者数" followed by numbers

    # Split into per-department sections by looking for department name patterns
    # The PDF structure repeats: 分野 -> 課程名 -> 学科名 -> enrollment data
    sections = re.split(r"===PAGE===", full_text)

    current_dept_name = ""
    current_course = ""
    current_day_night = ""
    current_duration: int | None = None

    for section in sections:
        lines = section.strip().split("\n")

        # Look for department identification
        dept_name = ""
        course = ""
        day_night = ""
        duration: int | None = None
        capacity: int | None = None
        enrollment: int | None = None
        intl_students: int | None = None
        graduates: int | None = None
        advanced: int | None = None
        employed: int | None = None
        other: int | None = None
        prev_enrollment: int | None = None
        dropouts: int | None = None
        dropout_rate: float | None = None

        for i, line in enumerate(lines):
            line_norm = _norm(line)

            # Find department section: "分野 課程名 学科名" header
            if "学科名" in line_norm and "分野" in line_norm and not dept_name:
                # Check if data is on the SAME line (JEC pattern):
                # "工業 工業専門課程 AIシステム科 ○"
                if i + 1 < len(lines):
                    next_line = _norm(lines[i + 1])
                    # If next line has field+course+dept on one line
                    parts = next_line.split()
                    if len(parts) >= 3 and "課程" in next_line:
                        # Pattern: "分野 課程名 学科名 [○]"
                        for pi, p in enumerate(parts):
                            if "課程" in p:
                                course = p
                                if pi + 1 < len(parts):
                                    dept_candidate = parts[pi + 1]
                                    if dept_candidate not in ("○", ""):
                                        dept_name = dept_candidate
                                break
                    elif next_line and "修業" not in next_line and "昼夜" not in next_line:
                        # Tohogakuen pattern: dept name alone on next line
                        dept_name = next_line
                        # Course on the line after that
                        if i + 2 < len(lines):
                            course_line = _norm(lines[i + 2])
                            cm2 = re.search(r"([\u4e00-\u9fff]+(?:専門)?課程)", course_line)
                            if cm2:
                                course = cm2.group(1)

            # Course name (standalone)
            if not course:
                cm = re.search(r"(?:課程名|課程)[：:\s]+(.+)", line_norm)
                if cm:
                    course = _norm(cm.group(1))

            # Day/night and duration
            if not day_night:
                dnm = re.search(r"(\d+)年\s*(昼|夜)", line_norm)
                if dnm:
                    duration = int(dnm.group(1))
                    day_night = dnm.group(2)
                else:
                    dnm2 = re.search(r"(昼|夜)\s*.*?(\d+).*?時間", line_norm)
                    if dnm2:
                        day_night = dnm2.group(1)

            # Enrollment data: "生徒総定員数 生徒実員 うち留学生数"
            if "生徒総定員" in line_norm or "定員数" in line_norm:
                # Numbers on this line or next line
                nums = _extract_ints(line_norm)
                if len(nums) >= 3:
                    capacity, enrollment, intl_students = nums[0], nums[1], nums[2]
                elif i + 1 < len(lines):
                    next_nums = _extract_ints(lines[i + 1])
                    if len(next_nums) >= 3:
                        capacity, enrollment, intl_students = next_nums[0], next_nums[1], next_nums[2]

            # Graduate data: "卒業者数 進学者数 就職者数"
            if "卒業者数" in line_norm and "進学" in line_norm:
                nums = _extract_ints(line_norm)
                if len(nums) >= 3:
                    graduates, advanced, employed = nums[0], nums[1], nums[2]
                    if len(nums) >= 4:
                        other = nums[3]
                elif i + 1 < len(lines):
                    next_nums = _extract_ints(lines[i + 1])
                    if len(next_nums) >= 3:
                        graduates, advanced, employed = next_nums[0], next_nums[1], next_nums[2]
                        if len(next_nums) >= 4:
                            other = next_nums[3]

            # Dropout data
            if "中退者" in line_norm or "中退率" in line_norm:
                nums = _extract_ints(line_norm)
                if nums:
                    prev_enrollment = nums[0] if len(nums) >= 1 else None
                    dropouts = nums[1] if len(nums) >= 2 else None
                # Dropout rate
                rm = re.search(r"(\d+\.?\d*)\s*[%％]", line_norm)
                if rm:
                    dropout_rate = float(rm.group(1))

        # If we found a department with enrollment data, record it
        if dept_name and enrollment is not None:
            # Clean department name (remove embedded day/night info)
            dept_clean = re.sub(r"\n.*", "", dept_name)
            dept_clean = re.sub(r"[（(].*?[）)]$", "", dept_clean).strip()

            departments.append(DepartmentRecord(
                name=dept_clean,
                course_name=course if course else None,
                duration_years=duration,
                day_or_evening=day_night if day_night else None,
                capacity=capacity,
                enrollment=enrollment,
                intl_students=intl_students,
                graduates=graduates,
                advanced=advanced,
                employed=employed,
                other=other,
                prev_enrollment=prev_enrollment,
                dropouts=dropouts,
                dropout_rate=dropout_rate,
            ))

    log.info("pdf_parsed", path=str(pdf_path), school=school_name, departments=len(departments))

    return SchoolAnnotation(
        school_name=school_name,
        school_type="専門学校",
        operator_name=operator_name,
        fiscal_year=fiscal_year,
        source_pdf=pdf_path.name,
        departments=departments,
    )
