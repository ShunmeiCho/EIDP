"""Convert Markdown report to PDF with Japanese font support + native diagrams.

Detects <!-- DIAGRAM:ARCH|FUNNEL|TIMELINE --> placeholders in markdown
and renders them as reportlab Drawings (avoids ASCII box-char alignment issues).

Usage: uv run python scripts/md_to_pdf.py <input.md> <output.pdf>
"""

import re
import sys
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --- Font Registration ---
FONT_CANDIDATES = [
    Path.home() / "Library" / "Fonts" / "NotoSansJP-VariableFont_wght.ttf",
    Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
]

BASE_FONT = None
for f in FONT_CANDIDATES:
    if f.exists():
        try:
            if f.suffix == ".ttc":
                pdfmetrics.registerFont(TTFont("JpFont", str(f), subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont("JpFont", str(f)))
            BASE_FONT = "JpFont"
            print(f"Using font: {f}")
            break
        except Exception as e:
            print(f"Font load failed: {f} ({e})")

if BASE_FONT is None:
    raise RuntimeError("No Japanese font found.")

# --- Colors ---
PRIMARY = HexColor("#1a1a2e")
ACCENT = HexColor("#c0392b")
OK_GREEN = HexColor("#27ae60")
WARN_ORANGE = HexColor("#e67e22")
BG_LIGHT = HexColor("#f5f5f5")
BG_CODE = HexColor("#f8f8f8")
BORDER = HexColor("#cccccc")
HEADER_BG = HexColor("#2c3e50")
HEADER_FG = HexColor("#ffffff")
BLUE = HexColor("#3498db")
PURPLE = HexColor("#9b59b6")


def make_styles() -> dict:
    s = {}
    s["title"] = ParagraphStyle(
        "Title", fontName=BASE_FONT, fontSize=20, leading=28,
        textColor=PRIMARY, spaceAfter=4 * mm,
    )
    s["meta"] = ParagraphStyle(
        "Meta", fontName=BASE_FONT, fontSize=9, leading=13,
        textColor=HexColor("#666666"), spaceAfter=6 * mm,
    )
    s["h1"] = ParagraphStyle(
        "H1", fontName=BASE_FONT, fontSize=16, leading=22,
        textColor=PRIMARY, spaceBefore=8 * mm, spaceAfter=4 * mm,
    )
    s["h2"] = ParagraphStyle(
        "H2", fontName=BASE_FONT, fontSize=13, leading=18,
        textColor=PRIMARY, spaceBefore=6 * mm, spaceAfter=3 * mm,
    )
    s["h3"] = ParagraphStyle(
        "H3", fontName=BASE_FONT, fontSize=11, leading=16,
        textColor=PRIMARY, spaceBefore=4 * mm, spaceAfter=2 * mm,
    )
    s["body"] = ParagraphStyle(
        "Body", fontName=BASE_FONT, fontSize=10, leading=15,
        textColor=HexColor("#222222"), spaceAfter=3 * mm,
    )
    s["bullet"] = ParagraphStyle(
        "Bullet", fontName=BASE_FONT, fontSize=10, leading=15,
        textColor=HexColor("#222222"), leftIndent=8 * mm, bulletIndent=4 * mm,
        spaceAfter=2 * mm,
    )
    return s


# --- Native Diagrams (avoid ASCII alignment issues) ---

def make_arch_diagram() -> Drawing:
    """3-layer architecture diagram: Input sources → Pipeline → Output."""
    W, H = 170 * mm, 160 * mm
    d = Drawing(W, H)

    # Layer 1: Input sources (top)
    inputs = [
        ("MEXT CSV", "学校マスタ"),
        ("既存Excel", "過去データ"),
        ("各学校サイト", "様式第2号 PDF"),
    ]
    box_w = 50 * mm
    box_h = 14 * mm
    gap = (W - 3 * box_w) / 4
    y_top = H - 18 * mm

    for i, (title, sub) in enumerate(inputs):
        x = gap + i * (box_w + gap)
        d.add(Rect(x, y_top, box_w, box_h, fillColor=HexColor("#ebf5fb"),
                   strokeColor=BLUE, strokeWidth=1.2, rx=2, ry=2))
        d.add(String(x + box_w / 2, y_top + box_h - 5 * mm, title,
                     fontName=BASE_FONT, fontSize=10, fillColor=PRIMARY,
                     textAnchor="middle"))
        d.add(String(x + box_w / 2, y_top + 2.5 * mm, sub,
                     fontName=BASE_FONT, fontSize=8, fillColor=HexColor("#666666"),
                     textAnchor="middle"))

    # Arrows down from each input
    arrow_y1 = y_top
    arrow_y2 = y_top - 6 * mm
    for i in range(3):
        x = gap + i * (box_w + gap) + box_w / 2
        d.add(Line(x, arrow_y1, x, arrow_y2, strokeColor=HexColor("#555555"),
                   strokeWidth=1.2))
        # arrowhead
        d.add(Polygon([x - 1.5 * mm, arrow_y2 + 1 * mm, x + 1.5 * mm,
                       arrow_y2 + 1 * mm, x, arrow_y2 - 1 * mm],
                      fillColor=HexColor("#555555"), strokeColor=HexColor("#555555")))

    # Layer 2: Pipeline box (middle)
    pipe_y = 38 * mm
    pipe_h = 102 * mm
    pipe_x = 8 * mm
    pipe_w = W - 16 * mm
    d.add(Rect(pipe_x, pipe_y, pipe_w, pipe_h, fillColor=HexColor("#fefbf3"),
               strokeColor=HexColor("#d4a017"), strokeWidth=1.5, rx=3, ry=3))
    d.add(String(pipe_x + pipe_w / 2, pipe_y + pipe_h - 6 * mm,
                 "EIDP 処理パイプライン (Venus GPU)",
                 fontName=BASE_FONT, fontSize=11, fillColor=PRIMARY,
                 textAnchor="middle"))

    # Steps inside pipeline
    steps = [
        ("Step 1", "Excel → DB 取り込み", OK_GREEN),
        ("Step 3", "MEXT学校コード マッチング (98.2%)", OK_GREEN),
        ("Step 4", "学校識別の統合 (Reconciler)", OK_GREEN),
        ("Step 7", "URL自動発見 (DDG + Firecrawl) — 91.5%", OK_GREEN),
        ("Step 8", "PDF自動ダウンロード — 4.8% ← ボトルネック", ACCENT),
        ("Step 9", "OCR (PaddleOCR PP-OCRv5) + 構文解析 — 23%", WARN_ORANGE),
        ("Step 10", "DB → Excel エクスポート (4シート)", OK_GREEN),
    ]
    step_h = 10 * mm
    step_w = pipe_w - 8 * mm
    step_x = pipe_x + 4 * mm
    start_y = pipe_y + pipe_h - 16 * mm
    for i, (num, desc, color) in enumerate(steps):
        y = start_y - (i + 1) * (step_h + 1 * mm)
        d.add(Rect(step_x, y, step_w, step_h, fillColor=HexColor("#ffffff"),
                   strokeColor=BORDER, strokeWidth=0.5, rx=1, ry=1))
        d.add(Rect(step_x, y, 18 * mm, step_h, fillColor=color,
                   strokeColor=color, strokeWidth=0.5))
        d.add(String(step_x + 9 * mm, y + step_h / 2 - 1.5 * mm, num,
                     fontName=BASE_FONT, fontSize=9, fillColor=HexColor("#ffffff"),
                     textAnchor="middle"))
        d.add(String(step_x + 20 * mm, y + step_h / 2 - 1.5 * mm, desc,
                     fontName=BASE_FONT, fontSize=9, fillColor=HexColor("#222222")))

    # Arrow from pipeline to output
    arrow_x = W / 2
    d.add(Line(arrow_x, pipe_y, arrow_x, pipe_y - 6 * mm,
               strokeColor=HexColor("#555555"), strokeWidth=1.2))
    d.add(Polygon([arrow_x - 1.5 * mm, pipe_y - 5 * mm,
                   arrow_x + 1.5 * mm, pipe_y - 5 * mm,
                   arrow_x, pipe_y - 7 * mm],
                  fillColor=HexColor("#555555"), strokeColor=HexColor("#555555")))

    # Layer 3: Outputs (bottom)
    outputs = [
        ("PostgreSQL", "データベース"),
        ("Excel", "レポート出力"),
        ("Review UI", "人手介入 Streamlit"),
    ]
    y_bot = 12 * mm
    for i, (title, sub) in enumerate(outputs):
        x = gap + i * (box_w + gap)
        d.add(Rect(x, y_bot, box_w, box_h, fillColor=HexColor("#eafaf1"),
                   strokeColor=OK_GREEN, strokeWidth=1.2, rx=2, ry=2))
        d.add(String(x + box_w / 2, y_bot + box_h - 5 * mm, title,
                     fontName=BASE_FONT, fontSize=10, fillColor=PRIMARY,
                     textAnchor="middle"))
        d.add(String(x + box_w / 2, y_bot + 2.5 * mm, sub,
                     fontName=BASE_FONT, fontSize=8, fillColor=HexColor("#666666"),
                     textAnchor="middle"))

    return d


def make_funnel_diagram() -> Drawing:
    """Funnel: 2067 → 2033 → 1827 → 87 → 20"""
    W, H = 170 * mm, 90 * mm
    d = Drawing(W, H)

    stages = [
        ("2,067 校", "MEXT 対象機関", "100%", OK_GREEN),
        ("2,033 校", "DB照合済み", "98.2%", OK_GREEN),
        ("1,827 校", "URL取得", "89.8%", OK_GREEN),
        ("   87 校", "PDF取得", "4.8% — ボトルネック", ACCENT),
        ("   20 校", "取り込み完了", "23% — OCR成功率", WARN_ORANGE),
    ]

    max_w = W - 40 * mm
    bar_h = 11 * mm
    gap = 3 * mm
    # Decreasing widths proportional to count (log scale to show all)
    widths = [max_w, max_w * 0.95, max_w * 0.88, max_w * 0.20, max_w * 0.08]

    for i, (count, label, pct, color) in enumerate(stages):
        y = H - 10 * mm - (i + 1) * (bar_h + gap)
        bar_w = widths[i]
        bar_x = (W - bar_w) / 2

        d.add(Rect(bar_x, y, bar_w, bar_h, fillColor=color, strokeColor=color,
                   strokeWidth=0, rx=2, ry=2))
        # count number on the bar
        d.add(String(bar_x + 4 * mm, y + bar_h / 2 - 1.5 * mm, count,
                     fontName=BASE_FONT, fontSize=10, fillColor=HexColor("#ffffff")))
        # label on right
        d.add(String(bar_x + bar_w + 3 * mm, y + bar_h / 2 - 1.5 * mm,
                     f"{label} — {pct}",
                     fontName=BASE_FONT, fontSize=9, fillColor=HexColor("#222222")))

        # arrow down (except for last)
        if i < len(stages) - 1:
            ax = W / 2
            ay = y - gap / 2
            d.add(Line(ax, y, ax, ay - 0.5 * mm,
                       strokeColor=HexColor("#555555"), strokeWidth=0.8))

    return d


def make_timeline_diagram() -> Drawing:
    """Timeline: Apr 21 → Jun 30 milestones."""
    W, H = 170 * mm, 80 * mm
    d = Drawing(W, H)

    # Horizontal axis
    axis_y = H - 12 * mm
    d.add(Line(10 * mm, axis_y, W - 10 * mm, axis_y,
               strokeColor=PRIMARY, strokeWidth=1.5))

    milestones = [
        ("4/21", "現在地", 0.0, PRIMARY),
        ("4/30", "KPI確定", 0.15, BLUE),
        ("5/15", "Path A/C 実施\n500-1000校", 0.42, BLUE),
        ("5/31", "setup.sh + cron\nテスト整備", 0.65, BLUE),
        ("6/15", "最終検証\nドキュメント", 0.85, BLUE),
        ("6/30", "納品完了", 1.0, ACCENT),
    ]

    axis_start = 12 * mm
    axis_end = W - 12 * mm
    axis_len = axis_end - axis_start

    for i, (date, label, pos, color) in enumerate(milestones):
        x = axis_start + pos * axis_len
        # Circle
        d.add(Rect(x - 2 * mm, axis_y - 2 * mm, 4 * mm, 4 * mm,
                   fillColor=color, strokeColor=color, strokeWidth=1))
        # Date above
        d.add(String(x, axis_y + 4 * mm, date,
                     fontName=BASE_FONT, fontSize=9, fillColor=PRIMARY,
                     textAnchor="middle"))
        # Label below (multi-line)
        label_lines = label.split("\n")
        for j, line in enumerate(label_lines):
            d.add(String(x, axis_y - 7 * mm - j * 4 * mm, line,
                         fontName=BASE_FONT, fontSize=8, fillColor=HexColor("#444444"),
                         textAnchor="middle"))

    # Title
    d.add(String(W / 2, H - 3 * mm, "2026年 プロジェクトタイムライン",
                 fontName=BASE_FONT, fontSize=11, fillColor=PRIMARY,
                 textAnchor="middle"))

    return d


DIAGRAM_RENDERERS = {
    "ARCH": make_arch_diagram,
    "FUNNEL": make_funnel_diagram,
    "TIMELINE": make_timeline_diagram,
}


def render_inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code) to reportlab HTML-like markup."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+?)`", r"<font backColor='#f0f0f0' color='#c0392b'>\1</font>", text)
    return text


def parse_table_block(lines: list[str], start: int) -> tuple[Table | None, int]:
    """Parse markdown table."""
    header_line = lines[start]
    if "|" not in header_line:
        return None, start + 1
    if start + 1 >= len(lines) or not re.match(r"^\s*\|?\s*[-:]+", lines[start + 1]):
        return None, start + 1

    headers = [c.strip() for c in header_line.strip().strip("|").split("|")]
    rows: list[list[str]] = []
    i = start + 2
    while i < len(lines):
        line = lines[i]
        if "|" not in line or line.strip() == "":
            break
        row = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))
        rows.append(row[: len(headers)])
        i += 1

    th_style = ParagraphStyle("TH", fontName=BASE_FONT, fontSize=9,
                               textColor=HEADER_FG, leading=12)
    td_style = ParagraphStyle("TD", fontName=BASE_FONT, fontSize=9,
                               textColor=HexColor("#222222"), leading=12)

    data = [[Paragraph(render_inline(c), th_style) for c in headers]]
    for row in rows:
        data.append([Paragraph(render_inline(c), td_style) for c in row])

    avail = 170 * mm
    ncols = len(headers)
    col_w = avail / ncols
    t = Table(data, colWidths=[col_w] * ncols, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for r in range(1, len(data)):
        if r % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, r), (-1, r), BG_LIGHT))
    t.setStyle(TableStyle(style_cmds))
    return t, i


def parse_code_block(lines: list[str], start: int) -> tuple[Preformatted | None, int]:
    """Parse fenced code block."""
    if not lines[start].startswith("```"):
        return None, start + 1
    i = start + 1
    code_lines = []
    while i < len(lines) and not lines[i].startswith("```"):
        code_lines.append(lines[i])
        i += 1
    if i >= len(lines):
        return None, start + 1
    code_text = "\n".join(code_lines)
    block = Preformatted(
        code_text,
        ParagraphStyle("Code", fontName=BASE_FONT, fontSize=7, leading=9,
                       textColor=HexColor("#333333"), backColor=BG_CODE,
                       borderPadding=4, leftIndent=4, rightIndent=4,
                       spaceAfter=3 * mm),
    )
    return block, i + 1


def parse_markdown(md_text: str, styles: dict) -> list:
    lines = md_text.split("\n")
    flows: list = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Diagram placeholder
        dm = re.match(r"^<!--\s*DIAGRAM:(\w+)\s*-->", line.strip())
        if dm:
            name = dm.group(1)
            if name in DIAGRAM_RENDERERS:
                flows.append(Spacer(1, 2 * mm))
                flows.append(DIAGRAM_RENDERERS[name]())
                flows.append(Spacer(1, 4 * mm))
            i += 1
            continue

        if line.startswith("```"):
            block, i = parse_code_block(lines, i)
            if block:
                flows.append(block)
                flows.append(Spacer(1, 2 * mm))
            continue

        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?\s*[-:]+", lines[i + 1]):
            t, i = parse_table_block(lines, i)
            if t:
                flows.append(t)
                flows.append(Spacer(1, 4 * mm))
            continue

        if re.match(r"^\s*---+\s*$", line):
            flows.append(HRFlowable(width="100%", thickness=0.5, color=BORDER,
                                    spaceBefore=4 * mm, spaceAfter=4 * mm))
            i += 1
            continue

        if line.startswith("# "):
            flows.append(Paragraph(render_inline(line[2:].strip()), styles["title"]))
            i += 1
            continue
        if line.startswith("## "):
            flows.append(Paragraph(render_inline(line[3:].strip()), styles["h1"]))
            i += 1
            continue
        if line.startswith("### "):
            flows.append(Paragraph(render_inline(line[4:].strip()), styles["h2"]))
            i += 1
            continue
        if line.startswith("#### "):
            flows.append(Paragraph(render_inline(line[5:].strip()), styles["h3"]))
            i += 1
            continue

        bm = re.match(r"^(\s*)[-*]\s+(.+)$", line)
        if bm:
            indent = len(bm.group(1))
            content = bm.group(2)
            style = styles["bullet"].clone("b", leftIndent=(4 + indent) * mm,
                                            bulletIndent=(2 + indent) * mm)
            flows.append(Paragraph(f"• {render_inline(content)}", style))
            i += 1
            continue

        nm = re.match(r"^(\s*)(\d+)\.\s+(.+)$", line)
        if nm:
            indent = len(nm.group(1))
            num = nm.group(2)
            content = nm.group(3)
            style = styles["bullet"].clone("b", leftIndent=(4 + indent) * mm,
                                            bulletIndent=(2 + indent) * mm)
            flows.append(Paragraph(f"{num}. {render_inline(content)}", style))
            i += 1
            continue

        if line.strip() == "":
            i += 1
            continue

        flows.append(Paragraph(render_inline(line), styles["body"]))
        i += 1

    return flows


def build_pdf(md_path: Path, output_path: Path) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    styles = make_styles()
    flows = parse_markdown(md_text, styles)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="EIDP プロジェクト進捗報告書",
        author="EIDP Team",
    )
    doc.build(flows)
    print(f"PDF generated: {output_path}")
    print(f"Size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run python scripts/md_to_pdf.py <input.md> <output.pdf>")
        sys.exit(1)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2])
    if not inp.exists():
        print(f"Input not found: {inp}")
        sys.exit(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(inp, out)
