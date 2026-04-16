"""PDF text extractor -- Step 9.

Extracts enrollment data from 機関要件確認申請書 PDFs.
Each department section in Form 2-4-2 contains:
- Header table with 分野, 課程名, 学科名, 専門士, 高度専門士
- 修業年限 and 昼夜 info
- 生徒総定員数 / 生徒実員 / うち留学生数 row
- 卒業者数 / 進学者数 / 就職者数 / その他 section
- 中途退学の現状 with 年度当初在学者数, 退学者の数, 中退率

2-tier: pdfplumber text extraction (Tier 1) -> MinerU/VL-OCR (Tier 2)
"""

import re
import unicodedata
from pathlib import Path

import structlog

from eidp.pdf.schema import DepartmentRecord, SchoolAnnotation, SupportRecipientRecord

log = structlog.get_logger()


def _norm(text: str | None) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def _extract_ints(text: str) -> list[int]:
    """Extract all integers from a text line."""
    return [int(x) for x in re.findall(r"\d+", text.replace(",", ""))]


def _extract_school_name(full_text: str) -> str:
    """Extract school name from PDF text.

    Looks for patterns:
    - 学校名 field in tables (most reliable, appears on many pages)
    - 大学等の名称 field on page 1
    """
    normed = _norm(full_text)

    # Pattern 1: 学校名 field (appears in many table headers)
    # e.g. "学校名 HAL東京" or "学校名 日本電子専門学校"
    # Also handles "学校名(学部等名)" variant in TCA
    m = re.search(r"学校名(?:\(学部等名\))?[\s:：]*(.+?)(?:\n|$)", normed)
    if m:
        name = m.group(1).strip()
        # Remove trailing labels that might be on the same line
        name = re.sub(r"\s*(?:設置者名|設置者|学校法人).*$", "", name)
        # Remove leading noise like "称】" from broken table extraction
        name = re.sub(r"^[称名】\]]+\s*", "", name)
        # Remove trailing "校長 XXX" pattern
        name = re.sub(r"\s*校長\s*.*$", "", name)
        if name:
            return name

    # Pattern 2: 大学等の名称 on page 1
    m = re.search(r"大学等の名称[\s:：]*(.+?)(?:\n|$)", normed)
    if m:
        name = m.group(1).strip()
        if name:
            return name

    return ""


def _extract_fiscal_year(full_text: str) -> str:
    """Extract fiscal year from PDF text.

    PDFs use date format like "令和７年６月２７日" (full-width digits).
    After NFKC normalization this becomes "令和7年6月27日".
    We extract the year number and produce "令和7年度".

    Priority order:
    1. 令和N年度 — direct, highest confidence
    2. 令和N年M月D日 — filing date on cover page
    3. Western date "YYYY.M.D" — filing date pattern (not stray year references)
    4. Most frequent western year — fallback, excludes future years
    """
    normed = _norm(full_text)

    # Pattern 1: 令和N年度 (direct match, highest confidence)
    m = re.search(r"令和(\d+)年度", normed)
    if m:
        return f"令和{m.group(1)}年度"

    # Pattern 2: 令和N年M月D日 (filing date, extract year)
    m = re.search(r"令和(\d+)年\d+月\d+日", normed)
    if m:
        return f"令和{m.group(1)}年度"

    # Pattern 3: Western filing date "YYYY.M.D" or "YYYY/M/D" pattern
    # These are actual filing dates, not stray year references in policy text
    filing_dates = re.findall(r"(202[0-9])[./]\d{1,2}[./]\d{1,2}", normed)
    if filing_dates:
        # Use the first filing date found (typically on the cover page)
        western_year = int(filing_dates[0])
        reiwa_year = western_year - 2018
        if reiwa_year > 0:
            return f"令和{reiwa_year}年度"

    # Pattern 4: Most frequent western year (fallback)
    # Exclude years beyond current+1 to avoid future policy references like "2027年度決算"
    from collections import Counter
    import datetime
    max_valid_year = datetime.date.today().year + 1
    all_years = re.findall(r"(202[0-9])[\.\s年/]", normed)
    valid_years = [int(y) for y in all_years if int(y) <= max_valid_year]
    if valid_years:
        most_common = Counter(valid_years).most_common(1)[0][0]
        reiwa_year = most_common - 2018
        if reiwa_year > 0:
            return f"令和{reiwa_year}年度"

    return ""


def _extract_operator_name(full_text: str) -> str:
    """Extract operator/founder name from PDF text.

    Looks for 設置者名 field in tables.
    """
    normed = _norm(full_text)

    m = re.search(r"設置者名[\s:：]*(.+?)(?:\n|$)", normed)
    if m:
        name = m.group(1).strip()
        if name:
            return name

    # Fallback: 設置者の名称 from page 1
    m = re.search(r"設置者の名称[\s:：]*(.+?)(?:\n|$)", normed)
    if m:
        name = m.group(1).strip()
        if name:
            return name

    return ""


def _parse_department_section(
    section_text: str,
    table_dept_name: str = "",
    table_course_name: str = "",
) -> DepartmentRecord | None:
    """Parse a single department section from PDF text.

    Each department section spans roughly 2 pages and contains:
    1. Header table: 分野 | 課程名 | 学科名 | 専門士 | 高度専門士
    2. Duration and day/night info: 修業年限 | 昼夜 | total hours
    3. Enrollment: 生徒総定員数, 生徒実員, うち留学生数
    4. Graduation: 卒業者数, 進学者数, 就職者数, その他
    5. Dropout: 年度当初在学者数, 退学者の数, 中退率

    table_dept_name/table_course_name: pre-extracted from pdfplumber table
    extraction (reliable). Used directly when available.
    """
    lines = section_text.strip().split("\n")
    normed_lines = [_norm(line) for line in lines]

    # Use table-extracted names (reliable) or fall back to text parsing
    dept_name = table_dept_name
    course = table_course_name

    # Text-only dept name extraction (fallback for OCR path where no table is available)
    if not dept_name:
        for i, line_norm in enumerate(normed_lines):
            # Pattern: "分野 | 課程名 | 学科名" header followed by data row
            if "学科名" in line_norm and ("分野" in line_norm or "課程名" in line_norm):
                # Next non-empty line after header should contain dept identity
                for j in range(i + 1, min(i + 3, len(normed_lines))):
                    candidate = normed_lines[j].strip()
                    # Skip header continuation lines
                    if candidate and "専門士" not in candidate and "高度専門士" not in candidate:
                        # Extract dept name: typically the longest token or the full line
                        parts = re.split(r"\s{2,}", candidate)
                        for part in parts:
                            cleaned = re.sub(r"\s+", "", part)
                            if len(cleaned) >= 3 and "専門課程" not in cleaned:
                                if not dept_name:
                                    dept_name = cleaned
                                elif not course and cleaned != dept_name:
                                    course = cleaned
                        if dept_name:
                            break
                if dept_name:
                    break
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

    for i, line_norm in enumerate(normed_lines):
        # -- Duration and day/night --
        # Pattern: "N年 昼" on same line, or "N年" and "昼/夜" separate
        if not duration:
            dm = re.search(r"(\d+)\s*年", line_norm)
            if dm and ("修業" in line_norm or "昼" in line_norm):
                duration = int(dm.group(1))
            elif dm and i > 0 and "修業" in normed_lines[i - 1]:
                duration = int(dm.group(1))

        if not day_night:
            # Match "昼" as day when it appears in duration/schedule context
            if re.search(r"(?:^|\s)昼(?:\s|$)", line_norm) and "昼夜" not in line_norm:
                day_night = "昼"
            elif re.search(r"(?:^|\s)夜(?:\s|$)", line_norm) and "昼夜" not in line_norm:
                day_night = "夜"

        # -- Enrollment data --
        # 生徒総定員数 | 生徒実員 | うち留学生数 row with numbers
        if "生徒総定員" in line_norm and "生徒実員" in line_norm:
            nums = _extract_ints(line_norm)
            if len(nums) >= 3:
                capacity, enrollment, intl_students = nums[0], nums[1], nums[2]
            elif i + 1 < len(normed_lines):
                next_nums = _extract_ints(normed_lines[i + 1])
                if len(next_nums) >= 3:
                    capacity, enrollment, intl_students = (
                        next_nums[0], next_nums[1], next_nums[2]
                    )

        # Also match the numbers-only line after header
        if enrollment is None and i > 0:
            prev = normed_lines[i - 1]
            if "生徒総定員" in prev or "定員数" in prev:
                nums = _extract_ints(line_norm)
                if len(nums) >= 3:
                    capacity, enrollment, intl_students = nums[0], nums[1], nums[2]

        # -- Graduation data --
        # Format in PDF (multi-line header):
        #   卒業者数、進学者数、就職者数(直近の年度の状況を記載)
        #             就職者数
        #   卒業者数 進学者数             その他
        #             (自営業を含む。)
        #   76人 5人 69人 2人
        #   (100%) ( 6.6%) ( 90.8%) ( 2.6%)
        #
        # Strategy: find "卒業者数" header line, then scan forward up to 6 lines
        # for the data row with "N人" pattern (4 numbers = grad, adv, emp, other)
        if graduates is None and "卒業者数" in line_norm and ("進学" in line_norm or "就職" in line_norm):
            # Scan forward for the data row
            for j in range(i, min(i + 7, len(normed_lines))):
                data_line = normed_lines[j]
                # Skip header/label lines
                if any(skip in data_line for skip in ["直近", "自営業", "状況を記載"]):
                    continue
                # Look for "N人" pattern (the data row)
                person_nums = re.findall(r"(\d+)\s*人", data_line)
                if len(person_nums) >= 3:
                    graduates = int(person_nums[0])
                    advanced = int(person_nums[1])
                    employed = int(person_nums[2])
                    if len(person_nums) >= 4:
                        other = int(person_nums[3])
                    break
                # Also handle "N (pct%) N (pct%) ..." format
                if graduates is None:
                    all_nums = _extract_ints(data_line)
                    pct_count = len(re.findall(r"\d+\.?\d*\s*[%％]", data_line))
                    if pct_count >= 3 and len(all_nums) >= 6:
                        # Interleaved: num, pct, num, pct, num, pct, num, pct
                        graduates = all_nums[0]
                        advanced = all_nums[2]
                        employed = all_nums[4]
                        if len(all_nums) >= 8:
                            other = all_nums[6]
                        break

        # -- Dropout data --
        # 中途退学の現状 section
        if "中途退学" in line_norm or "中退率" in line_norm:
            # Look for the data row with numbers (start from next line to skip header)
            for j in range(i + 1, min(i + 6, len(normed_lines))):
                data_line = normed_lines[j]
                # Dropout rate with % sign
                rm = re.search(r"(\d+\.?\d*)\s*[%％]", data_line)
                if rm and dropout_rate is None:
                    dropout_rate = float(rm.group(1))
                # Numbers line (skip header lines)
                if "年度当初" not in data_line and "途中" not in data_line:
                    nums = _extract_ints(data_line)
                    if len(nums) >= 2 and prev_enrollment is None:
                        prev_enrollment = nums[0]
                        dropouts = nums[1]

    if not dept_name or enrollment is None:
        return None

    # Clean department name: remove extra whitespace but keep parenthetical info
    dept_clean = re.sub(r"\s+", "", dept_name).strip()

    return DepartmentRecord(
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
    )


def _safe_int_from_text(text: str) -> int | None:
    """Extract a single integer from text like '342 人' or '-人'. Returns None for '-'."""
    cleaned = text.replace(",", "").replace("，", "").strip()
    if cleaned in ("-", "－", "―", ""):
        return None
    nums = re.findall(r"\d+", cleaned)
    if nums:
        return int(nums[0])
    return None


def _parse_support_section(page_texts: list[str]) -> SupportRecipientRecord | None:
    """Parse 対象比率 section from PDF pages.

    Finds the page containing "前年度の授業料等減免対象者" and extracts:
    - 支援対象者数: first_half / second_half / annual totals
    - 第I~IV区分: category breakdowns
    - 家計急変: household change count
    - 合計(年間): grand total

    Page detection: tries （別紙） anchor first (appendix marker),
    falls back to keyword detection. Handles multi-page appendix sections.
    """
    # Find the target page(s)
    target_page_idx = None

    # Strategy 1: Look for （別紙） anchor page with support recipient markers
    for i, pt in enumerate(page_texts):
        normed = _norm(pt)
        if "別紙" in normed and "授業料等減免対象者" in normed:
            target_page_idx = i
            break

    # Strategy 2: Fall back to keyword detection
    if target_page_idx is None:
        for i, pt in enumerate(page_texts):
            normed = _norm(pt)
            if "前年度の授業料等減免対象者" in normed and "支援対象者数" in normed:
                target_page_idx = i
                break

    if target_page_idx is None:
        return None

    # Combine target page + next page for multi-page appendix handling
    combined = page_texts[target_page_idx]
    if target_page_idx + 1 < len(page_texts):
        combined += "\n" + page_texts[target_page_idx + 1]
    normed = _norm(combined)
    lines = normed.split("\n")

    first_half_total: int | None = None
    second_half_total: int | None = None
    annual_total: int | None = None
    cat1_first: int | None = None
    cat1_second: int | None = None
    cat2_first: int | None = None
    cat2_second: int | None = None
    cat3_first: int | None = None
    cat3_second: int | None = None
    cat4_first: int | None = None
    cat4_second: int | None = None
    household_change: int | None = None
    grand_total: int | None = None

    for i, line in enumerate(lines):
        # Support recipients total line:
        # "※括弧内は多子世帯の学生等(内数) 342 人 (-人) 328 人 (11人) 350 人 (15人)"
        if "支援対象者数" in line or ("括弧内は多子世帯" in line and "人" in line):
            # Extract all numbers (ignoring parenthetical multi-child counts)
            # Pattern: N 人 (Xperson) N 人 (Xperson) N 人 (Xperson)
            # We want the main numbers, not the parenthetical ones
            # Remove parenthetical content first
            cleaned = re.sub(r"\([^)]*\)", "", line)
            nums = re.findall(r"(\d+)\s*人", cleaned)
            if len(nums) >= 3:
                first_half_total = int(nums[0])
                second_half_total = int(nums[1])
                annual_total = int(nums[2])
            elif len(nums) >= 2:
                first_half_total = int(nums[0])
                second_half_total = int(nums[1])

        # Category lines: "第I区分 177 人 166 人"
        # With next-line continuation for wrapped layouts
        if "第I区分" in line and "第II" not in line and "第III" not in line and "第IV" not in line:
            nums = re.findall(r"(\d+)\s*人", line)
            if len(nums) >= 2:
                cat1_first = int(nums[0])
                cat1_second = int(nums[1])
            elif len(nums) >= 1:
                cat1_first = int(nums[0])
            elif i + 1 < len(lines):
                next_nums = re.findall(r"(\d+)\s*人", lines[i + 1])
                if len(next_nums) >= 2:
                    cat1_first = int(next_nums[0])
                    cat1_second = int(next_nums[1])

        if "第II区分" in line:
            nums = re.findall(r"(\d+)\s*人", line)
            if len(nums) >= 2:
                cat2_first = int(nums[0])
                cat2_second = int(nums[1])
            elif len(nums) >= 1:
                cat2_first = int(nums[0])
            elif i + 1 < len(lines):
                next_nums = re.findall(r"(\d+)\s*人", lines[i + 1])
                if len(next_nums) >= 2:
                    cat2_first = int(next_nums[0])
                    cat2_second = int(next_nums[1])

        if "第III区分" in line:
            nums = re.findall(r"(\d+)\s*人", line)
            if len(nums) >= 2:
                cat3_first = int(nums[0])
                cat3_second = int(nums[1])
            elif len(nums) >= 1:
                cat3_first = int(nums[0])
            elif i + 1 < len(lines):
                next_nums = re.findall(r"(\d+)\s*人", lines[i + 1])
                if len(next_nums) >= 2:
                    cat3_first = int(next_nums[0])
                    cat3_second = int(next_nums[1])

        if "第IV区分" in line and "理工農" in line:
            nums = re.findall(r"(\d+)\s*人", line)
            if len(nums) >= 2:
                cat4_first = int(nums[0])
                cat4_second = int(nums[1])
            elif len(nums) >= 1:
                cat4_first = int(nums[0])
            elif i + 1 < len(lines):
                next_nums = re.findall(r"(\d+)\s*人", lines[i + 1])
                if len(next_nums) >= 2:
                    cat4_first = int(next_nums[0])
                    cat4_second = int(next_nums[1])

        # Household change: "家計急変による\n0 人 (0人)"
        # Skip the disclaimer line "※家計急変による者を除く"
        if "家計急変" in line and "除く" not in line:
            # Number might be on this line or the next
            cleaned_line = re.sub(r"\([^)]*\)", "", line)
            nums = re.findall(r"(\d+)\s*人", cleaned_line)
            if nums:
                household_change = int(nums[0])
            elif i + 1 < len(lines):
                next_line = re.sub(r"\([^)]*\)", "", lines[i + 1])
                next_nums = re.findall(r"(\d+)\s*人", next_line)
                if next_nums:
                    household_change = int(next_nums[0])

        # Grand total: "合計(年間) 350 人 (15人)"
        if "合計" in line and "年間" in line:
            cleaned = re.sub(r"\([^)]*\)", "", line)
            nums = re.findall(r"(\d+)\s*人", cleaned)
            if nums:
                grand_total = int(nums[0])

    # Only return if we got meaningful data
    if first_half_total is None and second_half_total is None and grand_total is None:
        return None

    return SupportRecipientRecord(
        first_half_total=first_half_total,
        first_half_cat1=cat1_first,
        first_half_cat2=cat2_first,
        first_half_cat3=cat3_first,
        first_half_cat4=cat4_first,
        second_half_total=second_half_total,
        second_half_cat1=cat1_second,
        second_half_cat2=cat2_second,
        second_half_cat3=cat3_second,
        second_half_cat4=cat4_second,
        annual_total=annual_total,
        household_change=household_change,
        grand_total=grand_total,
    )


def _extract_dept_identity_from_table(page) -> tuple[str, str, int | None, str]:
    """Extract dept name, course name, duration, and day/night from table.

    Uses structured table parsing which handles multi-line cell content
    correctly, unlike text-based extraction which interleaves columns.
    Returns (dept_name, course_name, duration_years, day_night).
    """
    try:
        tables = page.extract_tables()
        if not tables or len(tables[0]) < 2:
            return "", "", None, ""

        header_row = tables[0][0]
        data_row = tables[0][1]
        h_str = [str(c or "") for c in header_row]

        # Find column indices by header content
        dept_idx = next((j for j, h in enumerate(h_str) if "学科名" in h), None)
        course_idx = next((j for j, h in enumerate(h_str) if "課程名" in h), None)

        dept_name = ""
        course_name = ""

        if dept_idx is not None and data_row[dept_idx]:
            dept_name = re.sub(r"\s+", "", data_row[dept_idx])

        if course_idx is not None and data_row[course_idx]:
            course_name = re.sub(r"\s+", "", data_row[course_idx])

        # Clean dept name: strip schedule/duration suffixes
        # Pattern: "放送芸術科昼間部(2年制)" -> "放送芸術科"
        # Pattern: "ゲーム4年制学科（ゲーム企画コース）" -> keep as-is (sub-course is identity)
        dept_name = re.sub(r"昼間部\(?[\d年制]*\)?$", "", dept_name)
        dept_name = re.sub(r"夜間部\(?[\d年制]*\)?$", "", dept_name)

        # Extract duration and day/night from table Row 4 if available
        duration: int | None = None
        day_night = ""
        if len(tables[0]) >= 5:
            row4 = tables[0][4]
            row4_str = " ".join(str(c or "") for c in row4)
            row4_clean = re.sub(r"\s+", "", row4_str)
            dm = re.search(r"(\d+)年", row4_clean)
            if dm:
                duration = int(dm.group(1))
            if "昼" in row4_clean and "昼夜" not in row4_clean:
                day_night = "昼"
            elif "夜" in row4_clean and "昼夜" not in row4_clean:
                day_night = "夜"

        return dept_name, course_name, duration, day_night
    except Exception as e:
        log.warning("table_extract_failed", error=str(e), error_type=type(e).__name__)
        return "", "", None, ""


def parse_pdf(pdf_path: Path) -> SchoolAnnotation:
    """Parse a 機関要件確認申請書 PDF."""
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        full_text = ""
        page_texts: list[str] = []
        page_objects: list = []
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            page_texts.append(page_text)
            page_objects.append(page)
            full_text += page_text + "\n===PAGE===\n"

        # Extract school-level info
        school_name = _extract_school_name(full_text)
        fiscal_year = _extract_fiscal_year(full_text)
        operator_name = _extract_operator_name(full_text)

        # Split into department sections
        departments: list[DepartmentRecord] = []

        # Find department section boundaries
        normed_pages = [_norm(pt) for pt in page_texts]
        dept_section_starts: list[int] = []
        for i, page_text in enumerate(normed_pages):
            # Require at least 2 of 3 markers (some PDFs split markers across tables/pages)
            markers = sum([
                "分野" in page_text,
                "学科名" in page_text,
                "生徒総定員" in page_text,
            ])
            # Exclude 様式第2号の4 (financial/management pages) which also
            # contain 分野/学科名/生徒総定員 in a non-enrollment context
            is_financial = "財務" in page_text or "経営情報の公表" in page_text
            if markers >= 2 and not is_financial:
                dept_section_starts.append(i)

        for idx, start_page in enumerate(dept_section_starts):
            if idx + 1 < len(dept_section_starts):
                end_page = dept_section_starts[idx + 1]
            else:
                end_page = len(normed_pages)

            # Extract dept identity from table (reliable, handles multi-line names)
            table_dept, table_course, table_duration, table_day_night = (
                _extract_dept_identity_from_table(page_objects[start_page])
            )

            section_text = "\n".join(normed_pages[start_page:end_page])
            dept = _parse_department_section(
                section_text,
                table_dept_name=table_dept,
                table_course_name=table_course,
            )
            # Override duration/day_night from table if text parsing missed them
            if dept is not None:
                if dept.duration_years is None and table_duration is not None:
                    dept = dept.model_copy(update={"duration_years": table_duration})
                if not dept.day_or_evening and table_day_night:
                    dept = dept.model_copy(update={"day_or_evening": table_day_night})
            if dept is not None:
                departments.append(dept)

    # Extract support recipient data (対象比率 section)
    support_recipient = _parse_support_section(page_texts)

    log.info(
        "pdf_parsed",
        path=str(pdf_path),
        school=school_name,
        departments=len(departments),
        has_support_data=support_recipient is not None,
    )

    return SchoolAnnotation(
        school_name=school_name,
        school_type="専門学校",
        operator_name=operator_name,
        fiscal_year=fiscal_year,
        source_pdf=pdf_path.name,
        departments=departments,
        support_recipient=support_recipient,
    )


def parse_pdf_ocr(pdf_path: Path, ocr_page_texts: list[str]) -> SchoolAnnotation:
    """Parse a PDF using pre-extracted OCR text (for image-only PDFs).

    Uses the same extraction logic as parse_pdf but with OCR-provided text
    instead of pdfplumber text extraction. Table extraction is not available
    for OCR text, so dept identity comes from text parsing only.
    """
    full_text = "\n===PAGE===\n".join(ocr_page_texts)

    school_name = _extract_school_name(full_text)
    fiscal_year = _extract_fiscal_year(full_text)
    operator_name = _extract_operator_name(full_text)

    departments: list[DepartmentRecord] = []
    normed_pages = [_norm(pt) for pt in ocr_page_texts]
    dept_section_starts: list[int] = []

    for i, page_text in enumerate(normed_pages):
        markers = sum([
            "分野" in page_text,
            "学科名" in page_text,
            "生徒総定員" in page_text,
        ])
        is_financial = "財務" in page_text or "経営情報の公表" in page_text
        if markers >= 2 and not is_financial:
            dept_section_starts.append(i)

    for idx, start_page in enumerate(dept_section_starts):
        if idx + 1 < len(dept_section_starts):
            end_page = dept_section_starts[idx + 1]
        else:
            end_page = len(normed_pages)

        section_text = "\n".join(normed_pages[start_page:end_page])
        # No table extraction for OCR — use text-only parsing
        dept = _parse_department_section(section_text)
        if dept is not None:
            departments.append(dept)

    support_recipient = _parse_support_section(ocr_page_texts)

    log.info(
        "pdf_parsed_ocr",
        path=str(pdf_path),
        school=school_name,
        departments=len(departments),
        has_support_data=support_recipient is not None,
    )

    return SchoolAnnotation(
        school_name=school_name,
        school_type="専門学校",
        operator_name=operator_name,
        fiscal_year=fiscal_year,
        source_pdf=pdf_path.name,
        departments=departments,
        support_recipient=support_recipient,
    )
