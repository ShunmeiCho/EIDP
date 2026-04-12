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

    Some PDFs (Tohogakuen, TCA) don't include the cover page with 令和 dates.
    For those, we look for western calendar dates (e.g. "2025.5.23") and convert
    to the Japanese fiscal year: 令和N年 = (western_year - 2018)年.
    """
    normed = _norm(full_text)

    # Pattern 1: 令和N年度 (direct match)
    m = re.search(r"令和(\d+)年度", normed)
    if m:
        return f"令和{m.group(1)}年度"

    # Pattern 2: 令和N年M月D日 (date on cover page, extract year)
    m = re.search(r"令和(\d+)年\d+月\d+日", normed)
    if m:
        return f"令和{m.group(1)}年度"

    # Pattern 3: Western calendar date (e.g. "2025.5.23" or "2025年")
    # Convert to 令和: 令和N年 = (western_year - 2018)年
    # Use the MAXIMUM year found to get the filing year
    years = re.findall(r"(202[0-9])[\.\s年/]", normed)
    if years:
        western_year = max(int(y) for y in years)
        reiwa_year = western_year - 2018
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


def _parse_department_section(section_text: str) -> DepartmentRecord | None:
    """Parse a single department section from PDF text.

    Each department section spans roughly 2 pages and contains:
    1. Header table: 分野 | 課程名 | 学科名 | 専門士 | 高度専門士
    2. Duration and day/night info: 修業年限 | 昼夜 | total hours
    3. Enrollment: 生徒総定員数, 生徒実員, うち留学生数
    4. Graduation: 卒業者数, 進学者数, 就職者数, その他
    5. Dropout: 年度当初在学者数, 退学者の数, 中退率
    """
    lines = section_text.strip().split("\n")
    normed_lines = [_norm(line) for line in lines]

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

    for i, line_norm in enumerate(normed_lines):
        # -- Department name from header table --
        # The header line contains: 分野 | 課程名 | 学科名 | 専門士 | 高度専門士
        # After pdfplumber extraction, the table columns are interleaved as text.
        # We collect all text between the header and "修業" row, then extract
        # the course name (contains 課程) and department name from the fragments.
        if "学科名" in line_norm and "分野" in line_norm and not dept_name:
            # Collect all lines between header and 修業 row
            fragments: list[str] = []
            for j in range(i + 1, min(i + 10, len(normed_lines))):
                data_line = normed_lines[j]
                if "修業" in data_line or "全課程" in data_line:
                    break
                if "授業時数" in data_line or "開設" in data_line:
                    break
                fragments.append(data_line)

            # Reassemble text from fragments.
            # pdfplumber extracts table columns left-to-right, producing
            # interleaved text. We need to separate:
            #   - 分野 (field name) -- discard
            #   - 課程名 (course name, contains X課程) -- extract
            #   - 学科名 (department name) -- extract
            #
            # Strategy: classify each fragment as course-part, dept-part, or
            # field-name based on presence of 課程 keyword. Handle multi-line
            # names by reassembling fragments in the same category.

            # Field name patterns (分野 column values)
            _field_names_list = [
                "工業関係", "文化・教養", "文化教養", "工業",
                "衛生", "商業実務", "教育・社会福祉", "服飾・家政",
            ]

            # Strategy: First, search for the course name in the ORIGINAL
            # (un-cleaned) fragment text. The course name is a well-known
            # pattern like "X専門課程". Then everything else is dept name.
            #
            # Common course names:
            # 工業専門課程, 放送専門課程, 文化・教養専門課程,
            # デジタル専門課程, etc.
            all_frag_text = " ".join(fragments)
            # Find course name in original text (may span fragments)
            all_frag_joined = re.sub(r"\s+", "", all_frag_text)
            cm = re.search(
                r"([\u4e00-\u9fff\u30fb\u30a0-\u30ff]+専門課程"
                r"|[\u4e00-\u9fff\u30fb\u30a0-\u30ff]+課程)",
                all_frag_joined,
            )
            if cm:
                course = cm.group(1)

            # Now extract dept name: collect tokens that are NOT part of
            # the field name or course name
            dept_tokens: list[str] = []

            for frag in fragments:
                cleaned = re.sub(r"[○\-－]", "", frag).strip()
                if not cleaned:
                    continue

                tokens = cleaned.split()
                for token in tokens:
                    token = token.strip()
                    if not token:
                        continue

                    # Skip standalone field names
                    is_field = False
                    for fn in sorted(_field_names_list, key=len, reverse=True):
                        if token == fn:
                            is_field = True
                            break
                    if is_field:
                        continue

                    # Skip tokens that are part of the course name
                    if course and token in course:
                        continue
                    # Skip tokens that are fragments of the course name
                    # (e.g. "文化・教養専" is prefix of "文化・教養専門課程")
                    if course:
                        is_course_frag = False
                        for fn in sorted(_field_names_list, key=len, reverse=True):
                            if token.startswith(fn):
                                remainder = token[len(fn):]
                                if remainder and remainder in course:
                                    is_course_frag = True
                                    break
                        if is_course_frag:
                            continue
                        # Also check if token itself is a substring of course
                        if len(token) <= len(course) and token in course:
                            continue

                    dept_tokens.append(token)

            dept_raw = "".join(dept_tokens)
            # Remove 昼間部(N年制) metadata suffix (Tohogakuen pattern)
            dept_raw = re.sub(r"昼間部\(?\d*年制?\)?$", "", dept_raw)
            dept_raw = dept_raw.strip()

            if dept_raw:
                dept_name = dept_raw

        # -- Duration and day/night --
        # Pattern: "N年 昼" on same line, or "N年" and "昼/夜" separate
        if not duration:
            dm = re.search(r"(\d+)\s*年", line_norm)
            if dm and "修業" in line_norm or (dm and "昼" in line_norm):
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
            # Look for the data row with numbers
            for j in range(i, min(i + 5, len(normed_lines))):
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


def parse_pdf(pdf_path: Path) -> SchoolAnnotation:
    """Parse a 機関要件確認申請書 PDF."""
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        full_text = ""
        page_texts: list[str] = []
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            page_texts.append(page_text)
            full_text += page_text + "\n===PAGE===\n"

    # Extract school-level info
    school_name = _extract_school_name(full_text)
    fiscal_year = _extract_fiscal_year(full_text)
    operator_name = _extract_operator_name(full_text)

    # Split into department sections
    # Each department page has "分野" + "学科名" in the header table
    departments: list[DepartmentRecord] = []

    # Find department section boundaries
    # Look for pages containing both "分野" and "学科名" -- these are dept start pages
    normed_pages = [_norm(pt) for pt in page_texts]
    dept_section_starts: list[int] = []
    for i, page_text in enumerate(normed_pages):
        if "分野" in page_text and "学科名" in page_text and "生徒総定員" in page_text:
            dept_section_starts.append(i)

    for idx, start_page in enumerate(dept_section_starts):
        # Each department section spans from this page to the next section start
        if idx + 1 < len(dept_section_starts):
            end_page = dept_section_starts[idx + 1]
        else:
            end_page = len(normed_pages)

        section_text = "\n".join(normed_pages[start_page:end_page])
        dept = _parse_department_section(section_text)
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
