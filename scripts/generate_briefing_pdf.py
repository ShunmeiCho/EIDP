"""Generate professor briefing PDF with Japanese fonts and highlighted confirmation items."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

# --- Font Registration ---
FONT_PATH = Path("/Users/shunmei/Library/Fonts/NotoSansJP-VariableFont_wght.ttf")
if FONT_PATH.exists():
    pdfmetrics.registerFont(TTFont("NotoSansJP", str(FONT_PATH)))
    BASE_FONT = "NotoSansJP"
else:
    pdfmetrics.registerFont(TTFont("HiraginoW3", "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", subfontIndex=0))
    BASE_FONT = "HiraginoW3"

# --- Colors ---
PRIMARY = HexColor("#1a1a2e")
ACCENT = HexColor("#c0392b")
ACCENT_BG = HexColor("#fdf2f2")
LIGHT_GRAY = HexColor("#f5f5f5")
BORDER_GRAY = HexColor("#cccccc")
TABLE_HEADER_BG = HexColor("#2c3e50")
TABLE_HEADER_FG = HexColor("#ffffff")
RESOLVED_GREEN = HexColor("#27ae60")
RESOLVED_BG = HexColor("#f0faf4")
NOTE_BLUE = HexColor("#2980b9")
NOTE_BG = HexColor("#edf6fc")


def make_styles():
    s = {}
    s["title"] = ParagraphStyle(
        "Title", fontName=BASE_FONT, fontSize=18, leading=26,
        textColor=PRIMARY, spaceAfter=4 * mm,
    )
    s["subtitle"] = ParagraphStyle(
        "Subtitle", fontName=BASE_FONT, fontSize=10, leading=14,
        textColor=HexColor("#666666"), spaceAfter=8 * mm,
    )
    s["h1"] = ParagraphStyle(
        "H1", fontName=BASE_FONT, fontSize=14, leading=20,
        textColor=PRIMARY, spaceBefore=8 * mm, spaceAfter=4 * mm,
    )
    s["h2"] = ParagraphStyle(
        "H2", fontName=BASE_FONT, fontSize=12, leading=17,
        textColor=ACCENT, spaceBefore=5 * mm, spaceAfter=3 * mm,
    )
    s["body"] = ParagraphStyle(
        "Body", fontName=BASE_FONT, fontSize=10, leading=16,
        textColor=PRIMARY, spaceAfter=3 * mm,
    )
    s["body_small"] = ParagraphStyle(
        "BodySmall", fontName=BASE_FONT, fontSize=9, leading=14,
        textColor=PRIMARY,
    )
    s["confirm_title"] = ParagraphStyle(
        "ConfirmTitle", fontName=BASE_FONT, fontSize=11, leading=16,
        textColor=ACCENT, spaceBefore=2 * mm, spaceAfter=1 * mm,
    )
    s["confirm_body"] = ParagraphStyle(
        "ConfirmBody", fontName=BASE_FONT, fontSize=10, leading=15,
        textColor=PRIMARY, spaceAfter=2 * mm,
    )
    s["resolved_title"] = ParagraphStyle(
        "ResolvedTitle", fontName=BASE_FONT, fontSize=11, leading=16,
        textColor=RESOLVED_GREEN, spaceBefore=2 * mm, spaceAfter=1 * mm,
    )
    s["note_body"] = ParagraphStyle(
        "NoteBody", fontName=BASE_FONT, fontSize=9, leading=14,
        textColor=NOTE_BLUE, spaceAfter=2 * mm,
    )
    s["footer"] = ParagraphStyle(
        "Footer", fontName=BASE_FONT, fontSize=8, leading=12,
        textColor=HexColor("#999999"),
    )
    return s


def p(style, text):
    return Paragraph(text, style)


def make_table(headers, rows, col_widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), TABLE_HEADER_FG),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LEADING", (0, 0), (-1, -1), 14),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))
    t.setStyle(TableStyle(style_cmds))
    return t


def make_confirm_box(st, number, title, body_lines):
    """Red-bordered box for items needing confirmation."""
    inner_data = [
        [p(st["confirm_title"], f"確認事項{number}：{title}")],
    ]
    for line in body_lines:
        inner_data.append([p(st["confirm_body"], line)])

    inner_table = Table(inner_data, colWidths=[155 * mm])
    inner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_BG),
        ("BOX", (0, 0), (-1, -1), 1.5, ACCENT),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([inner_table, Spacer(1, 4 * mm)])


def make_resolved_box(st, title, body_lines):
    """Green-bordered box for already resolved items."""
    inner_data = [
        [p(st["resolved_title"], f"確認済み：{title}")],
    ]
    for line in body_lines:
        inner_data.append([p(st["confirm_body"], line)])

    inner_table = Table(inner_data, colWidths=[155 * mm])
    inner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RESOLVED_BG),
        ("BOX", (0, 0), (-1, -1), 1.5, RESOLVED_GREEN),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([inner_table, Spacer(1, 4 * mm)])


def make_note_box(st, body_lines):
    """Blue-bordered info note box."""
    inner_data = []
    for line in body_lines:
        inner_data.append([p(st["note_body"], line)])

    inner_table = Table(inner_data, colWidths=[155 * mm])
    inner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NOTE_BG),
        ("BOX", (0, 0), (-1, -1), 1, NOTE_BLUE),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([inner_table, Spacer(1, 3 * mm)])


def build_pdf(output_path):
    st = make_styles()
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )
    story = []

    # --- Title ---
    story.append(p(st["title"], "在校生人数データ自動収集システム"))
    story.append(p(st["subtitle"], "ご報告資料　2026年4月11日"))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
    story.append(Spacer(1, 4 * mm))

    # --- Overview ---
    story.append(p(st["body"],
        "現在手作業で行っている「各大学・専門学校の在校生人数データの収集・転記作業」を"
        "自動化するシステムの設計を進めています。本資料では、調査結果・技術方針・"
        "ご確認いただきたい事項をまとめます。"
    ))

    # --- Section 1: Current State ---
    story.append(p(st["h1"], "1. 現状の確認"))
    story.append(p(st["body"],
        "いただいたExcelファイル（専門学校分）を分析した結果は以下のとおりです。"
    ))
    story.append(make_table(
        [p(st["body_small"], "項目"), p(st["body_small"], "数値")],
        [
            [p(st["body_small"], "専門学校の対象校数"), p(st["body_small"], "2,212校")],
            [p(st["body_small"], "対象法人数"), p(st["body_small"], "1,442法人")],
            [p(st["body_small"], "対象都道府県"), p(st["body_small"], "47")],
            [p(st["body_small"], "学科別データ行数"), p(st["body_small"], "約9,761件")],
            [p(st["body_small"], "2025年度の採録済み（〇）"), p(st["body_small"], "943校（43%）")],
            [p(st["body_small"], "2025年度の部分採録（△）"), p(st["body_small"], "804校（36%）")],
            [p(st["body_small"], "未採録・対象外等"), p(st["body_small"], "465校（21%）")],
        ],
        col_widths=[100 * mm, 60 * mm],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(make_note_box(st, [
        "※ 大学約700校分のデータについては、別途サンプルデータのご提供をお願いいたします。",
    ]))

    # --- Section 2: Automation Plan ---
    story.append(p(st["h1"], "2. 自動化の方針"))

    story.append(p(st["h2"], "ご依頼の工程への対応"))
    story.append(make_table(
        [p(st["body_small"], "ご依頼の工程"), p(st["body_small"], "自動化内容")],
        [
            [p(st["body_small"], "工程1：PDFの収集"),
             p(st["body_small"], "各校のウェブサイトからPDFを自動で発見・ダウンロード")],
            [p(st["body_small"], "工程2：年度チェック"),
             p(st["body_small"], "前年度データとの自動比較により令和8年度版かを判定")],
            [p(st["body_small"], "工程3：データ転記"),
             p(st["body_small"], "PDFからデータを自動抽出し、データベースに格納")],
            [p(st["body_small"], "工程4：競合校レポート更新"),
             p(st["body_small"], "週次で自動集計し、Excelファイルを生成")],
        ],
        col_widths=[55 * mm, 105 * mm],
    ))

    story.append(p(st["h2"], "段階的アプローチ"))
    story.append(p(st["body"],
        "一度に全自動化を目指すのではなく、段階的に自動化率を高めます。"
    ))
    story.append(make_table(
        [p(st["body_small"], "段階"), p(st["body_small"], "内容"),
         p(st["body_small"], "期間"), p(st["body_small"], "自動化率")],
        [
            [p(st["body_small"], "第0段階"), p(st["body_small"], "200校のサンプルで検証"),
             p(st["body_small"], "2週間"), p(st["body_small"], "—")],
            [p(st["body_small"], "第1段階"), p(st["body_small"], "各校のURL特定＋PDF発見"),
             p(st["body_small"], "2〜3週間"), p(st["body_small"], "70〜85%")],
            [p(st["body_small"], "第2段階"), p(st["body_small"], "テキスト型PDFのデータ抽出"),
             p(st["body_small"], "2〜3週間"), p(st["body_small"], "60〜80%")],
            [p(st["body_small"], "第3段階"), p(st["body_small"], "画像型PDF対応＋学科変更対応"),
             p(st["body_small"], "継続"), p(st["body_small"], "+10〜15%")],
            [p(st["body_small"], "第4段階"), p(st["body_small"], "週次の定期更新運用"),
             p(st["body_small"], "1週間"), p(st["body_small"], "—")],
        ],
        col_widths=[25 * mm, 65 * mm, 35 * mm, 35 * mm],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(p(st["body"], "<b>6月の公開開始までに第2段階まで完了を目指します。</b>"))

    story.append(p(st["h2"], "人手が残る部分"))
    story.append(p(st["body"],
        "完全自動化が難しい箇所は、システム内の「確認キュー」に入り、"
        "担当者が画面上で確認・修正します。ご指示の通り、学科変更が発生した場合は"
        "システム側でエラーを出し、人力で対応する方針とします。"
    ))
    for item in [
        "・自動で判定できなかった学校のURL確認（推定220〜440校）",
        "・画像のみのPDFの確認",
        "・学科の新設・廃止・改称・統合の対応（推定100〜300件）",
    ]:
        story.append(p(st["body"], item))
    story.append(p(st["body"], "<b>推定作業量：6〜8月の期間中、週2〜4時間程度</b>"))

    story.append(p(st["h2"], "NotebookLM等との比較"))
    story.append(p(st["body"],
        "ご提案のNotebookLM等にPDFを投入する方法も検討しました。"
        "今回は毎年繰り返す定型作業のため、構造化パイプラインの方が適しています。"
    ))
    story.append(make_table(
        [p(st["body_small"], "観点"),
         p(st["body_small"], "NotebookLM等"),
         p(st["body_small"], "構造化パイプライン（今回）")],
        [
            [p(st["body_small"], "毎年の繰り返し"),
             p(st["body_small"], "毎回手動投入が必要"),
             p(st["body_small"], "一度構築すれば自動で回る")],
            [p(st["body_small"], "週次の増分更新"),
             p(st["body_small"], "困難"),
             p(st["body_small"], "自動で差分検知・更新")],
            [p(st["body_small"], "数値の正確性"),
             p(st["body_small"], "回答にブレの可能性"),
             p(st["body_small"], "ルールベースで安定")],
            [p(st["body_small"], "監査・追跡"),
             p(st["body_small"], "難しい"),
             p(st["body_small"], "全データの出典PDFを記録")],
        ],
        col_widths=[40 * mm, 55 * mm, 65 * mm],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(make_note_box(st, [
        "※ NotebookLMは「過去データの横断分析・質問応答」には有効です。"
        "データベース構築後の補助ツールとして活用する余地があります。",
    ]))

    # --- Section 3: Validation Results ---
    story.append(p(st["h1"], "3. 初期検証の結果"))
    story.append(p(st["body"],
        "設計に先立ち、50校のサンプルで技術検証を実施しました。"
        "結果は想定以上に良好です。"
    ))
    story.append(make_table(
        [p(st["body_small"], "検証項目"),
         p(st["body_small"], "目標"),
         p(st["body_small"], "実測値"),
         p(st["body_small"], "判定")],
        [
            [p(st["body_small"], "学校URL発見率（50校テスト）"),
             p(st["body_small"], "95%以上"),
             p(st["body_small"], "<b>100%</b>（86%が高確信度）"),
             p(st["body_small"], "達成")],
            [p(st["body_small"], "文科省学校コード照合率"),
             p(st["body_small"], "85%以上"),
             p(st["body_small"], "<b>91%</b>（2,014/2,212校）"),
             p(st["body_small"], "達成")],
            [p(st["body_small"], "PDFテキスト抽出可否"),
             p(st["body_small"], "80%以上"),
             p(st["body_small"], "<b>100%</b>（4校全てテキスト型）"),
             p(st["body_small"], "達成")],
            [p(st["body_small"], "競合分類の自動マッチ率"),
             p(st["body_small"], "80%以上"),
             p(st["body_small"], "<b>85%</b>（精確一致）"),
             p(st["body_small"], "達成")],
        ],
        col_widths=[50 * mm, 30 * mm, 55 * mm, 25 * mm],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(make_note_box(st, [
        "※ 大学のPDFフォーマットは専門学校と異なることが判明しました。"
        "v1では専門学校に集中し、大学は別途対応することを推奨します。",
    ]))

    # --- Section 4: Confirmation Items ---
    story.append(p(st["h1"], "4. ご確認いただきたい事項"))

    # Resolved items (green)
    story.append(make_resolved_box(st, "学科変更時の取り扱い", [
        "ご指示に従い、学科の統合・分割・新設・廃止等が発生した場合は"
        "システムがエラーを出力し、人力で対応する方針とします。",
    ]))

    story.append(make_resolved_box(st, "学校の識別方法", [
        "文部科学省の「学校コード」を利用します。検証の結果、2,212校中2,014校"
        "（91%）が自動照合可能であることを確認しました。残り198校は初回のみ"
        "手動で対応付けを行います。",
    ]))

    story.append(make_resolved_box(st, "大学の取り扱い", [
        "検証の結果、大学のPDFフォーマットは専門学校と異なることが判明しました。"
        "v1では専門学校（2,071校）に集中し、大学（773校）は別途対応とします。",
    ]))

    story.append(p(st["body"],
        "以下の3点について、ご判断・ご確認をお願いいたします。"
    ))

    # Confirm 1: Target scope
    story.append(make_confirm_box(st, 1, "対象校の範囲", [
        "Excel上に「学校なし」「閉校」「統合」「対象外」と記載されている"
        "学校（計155校）は、自動収集の対象から除外してよろしいでしょうか。"
        "（除外後の対象校数：2,057校）",
    ]))

    # Confirm 2: Taxonomy
    story.append(make_confirm_box(st, 2, "競合校レポートの分野分類", [
        "「競合校の在校生数」ファイルでは15の分野カテゴリ（ゲーム、IT、マンガ・"
        "アニメ等）に分類されていますが、この分類ルール（どの学科名がどの分野に"
        "該当するか）を明文化する必要があります。検証では85%が自動分類可能でしたが、"
        "残り15%の判断基準をお教えいただけますか。",
    ]))

    # Confirm 3: Operations
    story.append(make_confirm_box(st, 3, "運用体制", [
        "・確認作業（週2〜4時間）は、アルバイトの方が担当する想定で"
        "よろしいでしょうか。",
        "・システムの設置先は、学内PC（Linux）とクラウドの"
        "どちらが望ましいでしょうか。",
        "・Google検索APIの利用（各校の公開ページ発見のため）について、"
        "学内方針上の制約はありますか。",
    ]))

    # --- Section 5: Risks ---
    story.append(p(st["h1"], "5. 想定されるリスク"))
    story.append(make_table(
        [p(st["body_small"], "リスク"), p(st["body_small"], "影響"),
         p(st["body_small"], "対策")],
        [
            [p(st["body_small"], "学校サイトがPDFを遅れて公開"),
             p(st["body_small"], "収集漏れ"),
             p(st["body_small"], "週次で自動再チェック")],
            [p(st["body_small"], "画像のみのPDFが多い場合"),
             p(st["body_small"], "OCR精度低下"),
             p(st["body_small"], "該当校は確認キューで人手対応")],
            [p(st["body_small"], "学校サイトのアクセス制限"),
             p(st["body_small"], "PDF取得不可"),
             p(st["body_small"], "ブラウザ自動化で対応")],
            [p(st["body_small"], "学科の大幅な改組"),
             p(st["body_small"], "自動対応困難"),
             p(st["body_small"], "エラー出力＋人力対応（ご指示済み）")],
        ],
        col_widths=[55 * mm, 35 * mm, 70 * mm],
    ))

    # --- Section 6: Next Steps ---
    story.append(p(st["h1"], "6. 次のステップ"))
    for item in [
        "<b>1.</b> 上記の確認事項についてご判断をいただく",
        "<b>2.</b>（大学分のサンプルデータをいただく）",
        "<b>3.</b> 第0段階（200校サンプル検証）を開始",
        "<b>4.</b> 2週間後に検証結果をご報告",
    ]:
        story.append(p(st["body"], item))

    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY))
    story.append(p(st["footer"], "以上"))

    doc.build(story)


if __name__ == "__main__":
    output = Path("/Users/shunmei/workspace/EIDP/docs/plans/2026-04-11-briefing-for-professor.pdf")
    build_pdf(output)
    print(f"PDF generated: {output}")
    print(f"Size: {output.stat().st_size / 1024:.1f} KB")
