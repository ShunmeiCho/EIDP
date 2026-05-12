"""PDF text extractor -- Step 9.

Extracts enrollment data from 機関要件確認申請書 PDFs.
Each department section in Form 2-4-2 contains:
- Header table with 分野, 課程名, 学科名, 専門士, 高度専門士
- 修業年限 and 昼夜 info
- 生徒総定員数 / 生徒実員 / うち留学生数 row
- 卒業者数 / 進学者数 / 就職者数 / その他 section
- 中途退学の現状 with 年度当初在学者数, 退学者の数, 中退率

2-tier: pdfplumber text extraction (Tier 1) -> PaddleOCR/PyMuPDF OCR (Tier 2)
"""

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

from eidp.fiscal_year import current_fiscal_year, fiscal_year_from_japanese_era_text, format_fiscal_year_as_japanese_era
from eidp.pdf.schema import DepartmentRecord, SchoolAnnotation, SupportRecipientRecord

log = structlog.get_logger()

JST = timezone(timedelta(hours=9))
MIN_SUPPORTED_FISCAL_YEAR = 2019
MAX_SUPPORTED_FISCAL_YEAR = 2099


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


def _current_jst_fiscal_year() -> int:
    return current_fiscal_year(datetime.now(JST))


def _format_fiscal_year_if_allowed(fiscal_year: int | None, max_fiscal_year: int | None = None) -> str | None:
    if fiscal_year is None:
        return None
    if fiscal_year < MIN_SUPPORTED_FISCAL_YEAR or fiscal_year > MAX_SUPPORTED_FISCAL_YEAR:
        return None
    cap = min(_current_jst_fiscal_year() if max_fiscal_year is None else max_fiscal_year, MAX_SUPPORTED_FISCAL_YEAR)
    if fiscal_year > cap:
        return None
    return format_fiscal_year_as_japanese_era(fiscal_year) or f"{fiscal_year}年度"


def _extract_fiscal_year(full_text: str, *, max_fiscal_year: int | None = None) -> str:
    """Extract fiscal year from PDF text.

    PDFs often use date format like "令和７年６月２７日" (full-width digits).
    After NFKC normalization this becomes "令和7年6月27日". The western
    fiscal year remains the canonical value; era labels are output aliases.

    Priority order:
    1. 令和N年度 — direct, highest confidence
    2. 令和N年M月D日 — filing date on cover page
    3. Western date "YYYY.M.D" — filing date pattern (not stray year references)
    4. Most frequent western year — fallback, excludes future years
    """
    normed = _norm(full_text)

    # Pattern 1: 令和N年度 (direct match, highest confidence)
    fiscal_year = fiscal_year_from_japanese_era_text(
        normed,
        include_fiscal_year_labels=True,
        include_filing_dates=False,
    )
    formatted = _format_fiscal_year_if_allowed(fiscal_year, max_fiscal_year)
    if formatted:
        return formatted

    # Pattern 2: 令和N年M月D日 (filing date, extract year)
    fiscal_year = fiscal_year_from_japanese_era_text(
        normed,
        include_fiscal_year_labels=False,
        include_filing_dates=True,
    )
    formatted = _format_fiscal_year_if_allowed(fiscal_year, max_fiscal_year)
    if formatted:
        return formatted

    # Pattern 3: Western filing date "YYYY.M.D" or "YYYY/M/D" pattern
    # These are actual filing dates, not stray year references in policy text
    filing_dates = re.findall(r"(20\d{2})[./]\d{1,2}[./]\d{1,2}", normed)
    if filing_dates:
        # Use the first filing date found (typically on the cover page)
        western_year = int(filing_dates[0])
        formatted = _format_fiscal_year_if_allowed(western_year, max_fiscal_year)
        if formatted:
            return formatted

    # Pattern 4: Most frequent western year (fallback)
    # Exclude unsupported/future fiscal years to avoid unrelated policy/history references.
    from collections import Counter
    max_valid_year = _current_jst_fiscal_year() if max_fiscal_year is None else max_fiscal_year
    all_years = re.findall(r"(20\d{2})[\.\s年/]", normed)
    valid_years = [int(y) for y in all_years if MIN_SUPPORTED_FISCAL_YEAR <= int(y) <= max_valid_year]
    if valid_years:
        most_common = Counter(valid_years).most_common(1)[0][0]
        formatted = _format_fiscal_year_if_allowed(most_common, max_fiscal_year)
        if formatted:
            return formatted

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
            # Pattern 1: "分野 | 課程名 | 学科名" all on same line (pdfplumber)
            # Pattern 2: "学科名" on its own line (OCR split)
            header_on_same_line = "学科名" in line_norm and ("分野" in line_norm or "課程名" in line_norm)
            # OCR: "学科名" alone, and nearby lines have "分野"
            header_ocr_split = (
                "学科名" in line_norm
                and "分野" not in line_norm
                and any("分野" in normed_lines[k] for k in range(max(0, i - 3), i))
            )
            if header_on_same_line or header_ocr_split:
                # OCR layout: after "学科名" line, expect:
                #   専門士 / 高度専門士 / <分野値> / <課程名値> / <学科名値>
                # Collect candidates, pick the one that looks like a dept name
                _skip_labels = {"専門士", "高度専門士", "学科名", "分野", "課程名", "昼夜"}
                # MEXT 8 official fields (分野) with short/full variants:
                #   工業関係, 農業関係, 医療関係, 衛生関係,
                #   教育・社会福祉関係, 商業実務関係, 服飾・家政関係, 文化・教養関係
                # Match both short form ("工業") and full ("工業関係", "文化・教養関係")
                _field_pattern = re.compile(
                    r"^(工業|農業|医療|衛生|教育|社会福祉|商業|商業実務"
                    r"|服飾|家政|服飾・家政|文化|教養|文化・教養|教育・社会福祉)"
                    r"(関係)?$"
                )
                candidates: list[str] = []
                for j in range(i + 1, min(i + 12, len(normed_lines))):
                    candidate = normed_lines[j].strip()
                    if not candidate or any(s in candidate for s in _skip_labels):
                        continue
                    # Stop scanning at actual enrollment/curriculum sections
                    # (but NOT at 修業 alone — OCR sometimes emits 修業年限 mid-header)
                    if any(k in candidate for k in ["生徒総定員", "生徒実員", "カリキュラム"]):
                        break
                    cleaned = re.sub(r"\s+", "", candidate)
                    if _is_template_header_text(cleaned):
                        continue
                    if len(cleaned) >= 2:
                        candidates.append(cleaned)

                # From candidates: skip 分野 values, detect 課程名 vs 学科名
                for c in candidates:
                    if _field_pattern.match(c):
                        continue
                    # 修業年限 label/value should not be dept name
                    if c in ("修業", "修業年限") or re.match(r"^\d+年?$", c):
                        continue
                    if "専門課程" in c:
                        if not course:
                            course = c
                        continue
                    if not dept_name:
                        dept_name = c
                    elif not course and c != dept_name:
                        course = c
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
        # OCR may split across lines:
        #   "生徒総定員" on one line, "生徒実員" on next
        #   Or even "生徒総定" split from "員数" (OCR column wrap)
        # OCR layout: labels span ~6 lines, then data lines with "N人" follow
        enrollment_header_match = (
            "生徒総定員" in line_norm
            or (line_norm.strip() == "生徒総定"
                and any("員数" in normed_lines[k]
                        for k in range(i + 1, min(i + 10, len(normed_lines)))))
        )
        if enrollment is None and enrollment_header_match and "生徒実員" not in line_norm:
            # OCR layout: labels on separate lines, then each number on its own line
            # e.g. "40人" / "30人" / "0人" (or "V0" as OCR error for 0人)
            # Page-break tolerant: scan wider window, only hard-break on next section header
            found_nums: list[int] = []
            for j in range(i + 1, min(i + 25, len(normed_lines))):
                data_line = normed_lines[j].strip()
                # Hard break only on next major section header (not mid-section 概要 labels)
                if any(k in data_line for k in [
                    "授業計画作成と公表",
                    "成績評価の基準",
                    "卒業・進級",
                    "学修支援等",
                ]):
                    break
                # Match "N人" pattern
                person_match = re.findall(r"(\d+)\s*人", data_line)
                if person_match:
                    found_nums.extend(int(n) for n in person_match)
                # OCR misreads of standalone "0人" as V0/Y0/O0 (not mid-token)
                # Only match if line is EXACTLY the misread pattern (1-3 chars total)
                elif len(data_line) <= 3 and re.match(r"^[VYO]0$", data_line):
                    found_nums.append(0)
                if len(found_nums) >= 3:
                    capacity, enrollment, intl_students = found_nums[0], found_nums[1], found_nums[2]
                    break

        if "生徒総定員" in line_norm and "生徒実員" in line_norm:
            nums = _extract_ints(line_norm)
            if len(nums) >= 3:
                capacity, enrollment, intl_students = nums[0], nums[1], nums[2]
            elif i + 1 < len(normed_lines):
                # Handle multi-line with "N人" pattern (e.g., "105人 84人 0人...")
                next_line = normed_lines[i + 1]
                # Strip parenthetical content like "(116の内数)" before extracting
                clean_next = re.sub(r"\([^)]*\)", "", next_line)
                next_nums = _extract_ints(clean_next)
                if len(next_nums) >= 3:
                    capacity, enrollment, intl_students = (
                        next_nums[0], next_nums[1], next_nums[2]
                    )
                else:
                    next_nums = _extract_ints(next_line)
                    if len(next_nums) >= 3:
                        capacity, enrollment, intl_students = (
                            next_nums[0], next_nums[1], next_nums[2]
                        )
                    # Handle split across 2 lines: "35(116の" + "160人 0人..."
                    elif i + 2 < len(normed_lines):
                        combined = next_line + " " + normed_lines[i + 2]
                        clean_combined = re.sub(r"\([^)]*\)", "", combined)
                        combined_nums = re.findall(r"(\d+)\s*人", clean_combined)
                        if len(combined_nums) >= 3:
                            capacity, enrollment, intl_students = (
                                int(combined_nums[0]), int(combined_nums[1]), int(combined_nums[2])
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
        # OCR: "卒業者数" may appear alone; check nearby for "進学" or "就職"
        grad_header_same_line = "卒業者数" in line_norm and ("進学" in line_norm or "就職" in line_norm)
        grad_header_ocr = (
            "卒業者数" in line_norm
            and "進学" not in line_norm
            and any("進学" in normed_lines[k] or "就職" in normed_lines[k]
                    for k in range(i, min(i + 4, len(normed_lines))))
        )
        if graduates is None and (grad_header_same_line or grad_header_ocr):
            # Scan forward and accumulate N人 across lines
            # OCR puts each value on its own line: 33人 / 4人 / 22人 / 7人
            grad_nums: list[int] = []
            for j in range(i + 1, min(i + 12, len(normed_lines))):
                data_line = normed_lines[j]
                if any(skip in data_line for skip in ["直近", "自営業", "状況を記載"]):
                    continue
                # Stop on percentage lines (next section). Matches:
                #   (100%), ( 6.6%), bare 100%, 6.6%, etc.
                stripped = data_line.strip()
                if re.match(r"^\(?\s*\d+(?:\.\d+)?\s*%", stripped):
                    break
                person_nums = re.findall(r"(\d+)\s*人", data_line)
                person_unit_count = data_line.count("人")
                if person_nums:
                    if len(person_nums) < 3 and person_unit_count >= 4:
                        graduates = int(person_nums[0])
                        if len(person_nums) >= 2:
                            employed = int(person_nums[1])
                        break
                    grad_nums.extend(int(n) for n in person_nums)
                # Accumulate until we have 4 values, then break
                if len(grad_nums) >= 4:
                    break
                # Accept 3 values if we've scanned enough
                if len(grad_nums) >= 3 and j - i >= 8:
                    break

            if len(grad_nums) >= 3:
                graduates = grad_nums[0]
                advanced = grad_nums[1]
                employed = grad_nums[2]
                if len(grad_nums) >= 4:
                    other = grad_nums[3]

            # Fallback: original single-line scan (for pdfplumber path)
            for j in range(i, min(i + 7, len(normed_lines))):
                if graduates is not None:
                    break
                data_line = normed_lines[j]
                if any(skip in data_line for skip in ["直近", "自営業", "状況を記載"]):
                    continue
                person_nums = re.findall(r"(\d+)\s*人", data_line)
                person_unit_count = data_line.count("人")
                if 0 < len(person_nums) < 3 and person_unit_count >= 4:
                    graduates = int(person_nums[0])
                    if len(person_nums) >= 2:
                        employed = int(person_nums[1])
                    break
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

    # Clean department name: remove extra whitespace and Markdown artifacts
    dept_clean = re.sub(r"\s+", "", dept_name).strip()
    # Strip stray 〇/○ markers from text-fallback path
    dept_clean = re.sub(r"[〇○]", "", dept_clean)
    # Reject names that still contain Markdown pipe delimiters (OCR artifact)
    if "|" in dept_clean:
        return None
    # Strip leaked 分野 prefix from text-fallback concatenated lines
    # (e.g. "文化・教養グラフィックデザイン学科" -> "グラフィックデザイン学科")
    dept_clean = _strip_leading_field_prefix(dept_clean)
    # Final defense: if the cleaned name is itself just a 分野 term, reject
    if dept_clean in _FIELD_PREFIX_TERMS or _is_template_header_text(dept_clean):
        return None
    # Clean course_name too: strip 〇 markers and bare-分野 leakage
    course_clean = re.sub(r"[〇○]", "", course) if course else None
    if course_clean and course_clean in _FIELD_PREFIX_TERMS:
        course_clean = None

    # Detect dept/course column swap: if dept_clean looks like a 課程
    # (ends with 専門/本科 without 学科 marker) AND course_clean looks
    # like a 学科 (has 学科/科 suffix), swap them.
    if (
        _LIKELY_COURSE_NAME_RE.search(dept_clean)
        and not _HAS_DEPT_SUFFIX_RE.search(dept_clean)
        and course_clean
        and _HAS_DEPT_SUFFIX_RE.search(course_clean)
    ):
        dept_clean, course_clean = course_clean, dept_clean + "課程"

    return DepartmentRecord(
        name=dept_clean,
        course_name=course_clean if course_clean else None,
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


_TEMPLATE_HEADER_MARKERS = (
    "修業全課程",
    "全課程の修了",
    "開設している授業",
    "授業時数",
    "総単位数",
    "単位時間",
)
_TEMPLATE_NUMERIC_UNIT_RE = re.compile(r"\d+\s*(?:単位|時間)")


def _is_template_header_text(text: str) -> bool:
    """Reject table header/help text that OCR can place where department names live."""
    if any(marker in text for marker in _TEMPLATE_HEADER_MARKERS):
        return True
    if _TEMPLATE_NUMERIC_UNIT_RE.search(text):
        return True
    return False


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


_FIELD_DEDUPE_RE = re.compile(
    r"^(工業|農業|医療|衛生|教育|社会福祉|商業|商業実務|服飾|家政|文化|教養)\1"
)
# Ordered from longest to shortest so multi-char fields match first.
_FIELD_PREFIX_TERMS = (
    "文化・教養",
    "教育・社会福祉",
    "服飾・家政",
    "商業実務",
    "社会福祉",
    "文化教養",
    "教育社会福祉",
    "工業",
    "農業",
    "医療",
    "衛生",
    "教育",
    "商業",
    "服飾",
    "家政",
    "文化",
    "教養",
)
# Names ending with 専門/本科 (without 学科) are likely 課程 leaked into 学科 column
_LIKELY_COURSE_NAME_RE = re.compile(r"(専門|本科)$")
_HAS_DEPT_SUFFIX_RE = re.compile(r"(学科|学部|学院|専攻|コース|科)$")
_LEADING_FIELD_RE = re.compile(r"^(" + "|".join(_FIELD_PREFIX_TERMS) + r")(?=\S)")
_DEPT_SUFFIX_RE = re.compile(r"(学科|学部|学院|専攻|コース|課程|学校|科)$")


def _strip_leading_field_prefix(name: str) -> str:
    """Strip 分野 prefix leaked into dept/course name by merged-cell PDFs.

    Only strips if the remainder still looks like a valid dept identity
    (ends with 学科/学部/学院/専攻/コース/課程/学校/科) so legit names
    starting with 医療/教育/工業 (e.g. 医療事務科) survive.
    """
    m = _LEADING_FIELD_RE.match(name)
    if not m:
        return name
    stripped = name[m.end():]
    if len(stripped) >= 2 and _DEPT_SUFFIX_RE.search(stripped):
        return stripped
    return name


def _find_dept_table(tables: list[list[list]]) -> tuple[list[list] | None, int]:
    """Find the table containing the dept identity header row (学科名 + 課程名).

    Some PDFs put 学校名/設置者名 or 財務諸表 tables before the dept table,
    so we cannot assume tables[0] is the right one. Header may also live on
    rows 0/1/2 within a table, not just row 0.
    """
    for table in tables:
        if not table or len(table) < 2:
            continue
        for hidx in range(min(3, len(table) - 1)):
            row = table[hidx]
            if not row:
                continue
            joined = "".join(str(c or "") for c in row)
            if "学科名" in joined and "課程名" in joined:
                return table, hidx
    return None, -1


def _extract_dept_identity_from_table(page) -> tuple[str, str, int | None, str]:
    """Extract dept name, course name, duration, and day/night from table.

    Scans all tables for the dept identity header (学科名 + 課程名) instead
    of assuming tables[0]. Duration and 昼/夜 are searched dynamically among
    the rows below the header rather than at a fixed offset, so multi-section
    headers (e.g. 医療系 with separate 授業時数 sub-table) parse correctly.
    """
    try:
        tables = page.extract_tables()
        if not tables:
            return "", "", None, ""

        target_table, header_idx = _find_dept_table(tables)
        if target_table is None:
            return "", "", None, ""

        header_row = target_table[header_idx]
        data_row = target_table[header_idx + 1]
        h_str = [str(c or "") for c in header_row]

        dept_idx = next((j for j, h in enumerate(h_str) if "学科名" in h), None)
        course_idx = next((j for j, h in enumerate(h_str) if "課程名" in h), None)

        dept_name = ""
        course_name = ""

        if dept_idx is not None and dept_idx < len(data_row) and data_row[dept_idx]:
            dept_name = re.sub(r"\s+", "", data_row[dept_idx])

        if course_idx is not None and course_idx < len(data_row) and data_row[course_idx]:
            course_name = re.sub(r"\s+", "", data_row[course_idx])

        # Strip schedule/duration suffixes
        dept_name = re.sub(r"昼間部\(?[\d年制]*\)?$", "", dept_name)
        dept_name = re.sub(r"夜間部\(?[\d年制]*\)?$", "", dept_name)
        # Strip all 〇/○ markers (専門士 indicator that bled into the cell,
        # may appear at start/middle/end depending on cell merge direction).
        dept_name = re.sub(r"[〇○]", "", dept_name)
        course_name = re.sub(r"[〇○]", "", course_name)
        # Dedupe field-prefix repetition like "医療医療専門課程" -> "医療専門課程"
        course_name = _FIELD_DEDUPE_RE.sub(r"\1", course_name)
        # Strip single 分野 prefix leaked into dept name (merged-cell PDFs)
        dept_name = _strip_leading_field_prefix(dept_name)
        # course_name that is just a 分野 term (no 課程/本科) is leakage, not a course
        if course_name in _FIELD_PREFIX_TERMS:
            course_name = ""

        # Defensive: if extracted dept_name still looks like template/numeric junk,
        # discard it so the text fallback can try.
        if dept_name and _is_template_header_text(dept_name):
            dept_name = ""

        # Find duration/day_night row dynamically: scan rows after header for "X年" + 昼/夜
        duration: int | None = None
        day_night = ""
        for r in target_table[header_idx + 2 : header_idx + 8]:
            row_str = " ".join(str(c or "") for c in r)
            row_clean = re.sub(r"\s+", "", row_str)
            if not row_clean:
                continue
            dm = re.search(r"(\d+)年", row_clean)
            if dm and duration is None:
                duration = int(dm.group(1))
            if not day_night and "昼夜" not in row_clean:
                if "昼" in row_clean:
                    day_night = "昼"
                elif "夜" in row_clean:
                    day_night = "夜"
            if duration is not None and day_night:
                break

        return dept_name, course_name, duration, day_night
    except Exception as e:
        log.warning("table_extract_failed", error=str(e), error_type=type(e).__name__)
        return "", "", None, ""


def _is_course_breakdown_section(dept_name: str, section_text: str) -> bool:
    """Return True for course-level breakdown cards that should not become departments."""
    dept_norm = _norm(dept_name)
    if "コース" not in dept_norm:
        return False

    lines = _norm(section_text).split("\n")
    for i, line in enumerate(lines):
        if "生徒総定員" not in line and "定員数" not in line:
            continue
        window = "\n".join(lines[i : i + 4])
        if "内数" in window:
            return True
    return False


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
            # Exclude pages that are PURELY financial (様式第2号の4) without
            # actual enrollment data. Pages that have BOTH financial and enrollment
            # content (small school single-page PDFs) should be included.
            is_financial = "財務" in page_text or "経営情報の公表" in page_text
            has_enrollment = "生徒実員" in page_text
            if markers >= 2 and (not is_financial or has_enrollment):
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
            if _is_course_breakdown_section(table_dept, section_text):
                continue

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


def _clean_ocr_markdown(md_text: str) -> str:
    """Clean OCR output artifacts for parser consumption.

    Strips Markdown-like artifacts that some OCR engines produce:
    - Table pipes: | 学校名 | HAL東京 | → 学校名 HAL東京
    - Image links: ![](path/to/img.jpg) → removed
    - Header markers: ## Section → Section
    - Bold/italic: **text** → text
    """
    lines = md_text.split("\n")
    cleaned: list[str] = []

    for line in lines:
        # Remove image links
        line = re.sub(r"!\[.*?\]\(.*?\)", "", line)
        # Remove markdown header markers
        line = re.sub(r"^#{1,6}\s+", "", line)
        # Remove bold/italic markers
        line = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", line)

        # Handle Markdown table rows: | cell1 | cell2 | → cell1 cell2
        if "|" in line:
            # Skip table separator rows like |---|---|
            if re.match(r"^\|[\s\-:]+\|", line):
                continue
            # Extract cell contents, join with spaces
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if cells:
                line = " ".join(cells)

        # Remove remaining pipe characters that might be artifacts
        line = line.replace("|", " ").strip()

        if line:
            cleaned.append(line)

    return "\n".join(cleaned)


def parse_pdf_ocr(pdf_path: Path, ocr_page_texts: list[str]) -> SchoolAnnotation:
    """Parse a PDF using pre-extracted OCR text (for image-only PDFs).

    Cleans OCR output artifacts, then uses the same extraction logic
    as parse_pdf. Table extraction is not available for OCR text,
    so dept identity comes from text parsing only.
    """
    # Clean Markdown artifacts from OCR output
    cleaned_pages = [_clean_ocr_markdown(pt) for pt in ocr_page_texts]
    full_text = "\n===PAGE===\n".join(cleaned_pages)

    school_name = _extract_school_name(full_text)
    fiscal_year = _extract_fiscal_year(full_text)
    operator_name = _extract_operator_name(full_text)

    departments: list[DepartmentRecord] = []
    normed_pages = [_norm(pt) for pt in cleaned_pages]

    # Build merged line stream with page boundaries preserved
    # Each entry: (page_idx, line_text)
    all_lines: list[tuple[int, str]] = []
    for page_idx, page_text in enumerate(normed_pages):
        is_financial = "財務" in page_text or "経営情報の公表" in page_text
        if is_financial and "生徒実員" not in page_text:
            # Skip pure financial pages (but keep mixed pages with enrollment data)
            continue
        for line in page_text.split("\n"):
            all_lines.append((page_idx, line))

    # Header-anchor state machine: split on the "分野" header that
    # introduces a new department card (more reliable than page boundaries).
    # Each header anchor starts a new section; data accumulates until next
    # anchor or end of document.
    #
    # Anchor pattern (OCR): "分野" as standalone/short line followed by
    #                       "学科名" within ~8 lines
    # Anchor pattern (pdfplumber): "分野 | 課程名 | 学科名" all on same line
    #
    # To avoid body-text false positives, we require EITHER:
    #   A) same-line: "分野" AND "学科名" on same line (typical pdfplumber)
    #   B) OCR short line: "分野" on a line whose stripped length <= 5 chars
    #      (e.g., exactly "分野" / "分野名") followed by "学科名" and
    #      "課程名" both appearing in the next 8 lines
    section_starts: list[int] = []
    for idx, (_, line) in enumerate(all_lines):
        if "分野" not in line:
            continue
        stripped = line.strip()

        # Pattern A: same-line header
        if "分野" in stripped and "学科名" in stripped:
            section_starts.append(idx)
            continue

        # Pattern B: OCR short standalone line
        # Require stripped length <= 5 (rejects any body text containing 分野)
        if len(stripped) > 5:
            continue
        # Check both 学科名 AND 課程名 nearby (stronger signal than either alone)
        window = [all_lines[k][1] for k in range(idx + 1, min(idx + 9, len(all_lines)))]
        has_gakka = any("学科名" in w for w in window)
        has_katei = any("課程名" in w for w in window)
        if has_gakka and has_katei:
            section_starts.append(idx)

    # Parse each section
    for idx, start_line in enumerate(section_starts):
        end_line = section_starts[idx + 1] if idx + 1 < len(section_starts) else len(all_lines)
        section_text = "\n".join(line for _, line in all_lines[start_line:end_line])
        dept = _parse_department_section(section_text)
        if dept is not None:
            departments.append(dept)

    support_recipient = _parse_support_section(cleaned_pages)

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
