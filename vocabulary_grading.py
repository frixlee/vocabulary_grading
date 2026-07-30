import os
import re
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. 配置级别与高亮底色的对应关系
LEVEL_COLOR_MAP = {
    'A1': '#C8E6C9',  # 浅绿，实际未添加该词汇表
    'A2': '#A5D6A7',  # 薄荷绿
    'B1': '#81C784',  # 草绿
    'B2': '#4CAF50',  # 中绿
    'C1': '#2E7D32',  # 森绿
    'C2': '#1B5E20',  # 深松绿

    # 国内教纲级别示例：
    '小学': '#E3F2FD', # 水冰蓝，实际未添加该词汇表
    '初中': '#90CAF9', # 浅天蓝
    '高中': '#64B5F6', # 车矢菊蓝
    '四级': '#1565C0', # 深海蓝
    '六级': '#FFAB91', # 浅红
}
DEFAULT_BG_COLOR = '#FFFFFF'  # 默认底色白色

def get_bg_color(level_str):
    return LEVEL_COLOR_MAP.get(str(level_str).strip(), DEFAULT_BG_COLOR)

# ------------------------------------------------------------------
# V2新增页面装饰：竖直分隔线 + 页脚居中页码（通过画布回调绘制，贯穿整页）
# ------------------------------------------------------------------
PAGE_W, PAGE_H = A4
LEFT_MARGIN = 40
RIGHT_MARGIN = 40
TOP_MARGIN = 40
BOTTOM_MARGIN = 40

LEFT_WIDTH = 335
GAP_WIDTH = 35
RIGHT_WIDTH = (PAGE_W - LEFT_MARGIN - RIGHT_MARGIN) - LEFT_WIDTH - GAP_WIDTH  # 计算宽度位置145

# 竖直分隔线的 x 坐标
DIVIDER_X = LEFT_MARGIN + LEFT_WIDTH + GAP_WIDTH / 2.0

DIVIDER_COLOR = colors.HexColor('#D0D0D0')   # 浅灰分隔线
FOOTER_COLOR = colors.HexColor('#9E9E9E')    # 浅灰页码

def _draw_decorations(canvas, doc):
    # 每页底部正中画页码，并绘制一条贯穿页面的竖直分隔线。
    # 页码（底部居中）
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(FOOTER_COLOR)
    canvas.drawCentredString(
        PAGE_W / 2.0,
        BOTTOM_MARGIN / 2.0,
        f"第 {doc.page} 页"
    )

    # 竖直分隔线（从正文顶部延伸至页脚上方）
    canvas.setStrokeColor(DIVIDER_COLOR)
    canvas.setLineWidth(0.8)
    canvas.line(
        DIVIDER_X,
        PAGE_H - TOP_MARGIN,
        DIVIDER_X,
        BOTTOM_MARGIN
    )
    canvas.restoreState()

def create_annotated_pdf(text_file, vocab_file, output_pdf, font_path=None):
    """
    读取英文文本与 Excel 词汇表（A列单词, B列级别），生成带背景高亮及
    右侧级别标注的 PDF。v2 改进：
      1) 文章与单词之间加竖直分隔线，页脚正中加页码；
      2) 右侧单词跨全文去重（每个单词仅首次出现时列出一次）。
    """
    # 如果指定了中文字体路径，则注册字体（用于支持右侧显示中文级别说明）
    if font_path and os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('CustomFont', font_path))
        font_name_right = 'CustomFont'
    else:
        font_name_right = 'Helvetica'

    # 读取 Excel 词汇表 (A列单词, B列级别)
    df = pd.read_excel(vocab_file)
    vocab_dict = {}
    for _, row in df.iterrows():
        word = str(row.iloc[0]).strip().lower()
        level = str(row.iloc[1]).strip()
        if word and word != 'nan':
            vocab_dict[word] = level

    # 读取英文文稿
    with open(text_file, 'r', encoding='utf-8') as f:
        paragraphs = f.read().split('\n\n')

    # 创建 PDF 文档模板 (A4)
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        rightMargin=RIGHT_MARGIN,
        leftMargin=LEFT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN
    )
    styles = getSampleStyleSheet()

    # 左侧英文段落样式 (占约 2/3 宽)
    style_left = ParagraphStyle(
        name='EnglishStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=17,      # 行距
        alignment=4,     # 两端对齐
        rightIndent=14,  # 与分隔线保持间距
    )

    # 右侧级别标注样式 (占约 1/3 宽)
    style_right = ParagraphStyle(
        name='AnnotationStyle',
        parent=styles['Normal'],
        fontName=font_name_right,
        fontSize=9,
        leading=15,
        textColor=colors.HexColor('#424242'),
        leftIndent=14,   # 与分隔线保持间距
    )

    # --------------------------------------------------------------
    # 收集所有段落的左右内容，合并为单张 3 列表格：
    #   [ 左：文章 ] [ 中：一点留白 ] [ 右：单词 ]
    # 单张表格可跨页自动拆分，配合画布回调画出连续竖直分隔线。
    # --------------------------------------------------------------
    seen_words = set()          # 全局已列出的单词，用于去重
    rows = []

    for p_text in paragraphs:
        p_text = p_text.strip()
        if not p_text:
            continue

        # ReportLab 字符转义
        p_text = p_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        found_in_paragraph = {}

        # 按单词长度降序排列优先匹配长词，防止词干误替换
        for word in sorted(vocab_dict.keys(), key=len, reverse=True):
            level = vocab_dict[word]
            pattern = r'\b(' + re.escape(word) + r')\b'

            if re.search(pattern, p_text, flags=re.IGNORECASE):
                found_in_paragraph[word] = level
                bg_color = get_bg_color(level)

                # 使用 backcolor 设置文字底色高亮
                replacement = f'<font backcolor="{bg_color}">\\1</font>'
                p_text = re.sub(pattern, replacement, p_text, flags=re.IGNORECASE)

        # 构建右侧注释：仅保留本文档中尚未列出过的单词，V2新增去重功能
        new_words = [(w, lvl) for w, lvl in found_in_paragraph.items()
                     if w not in seen_words]
        # 按字母序排列，阅读更整洁
        new_words.sort(key=lambda x: x[0])

        annotations = []
        for w, lvl in new_words:
            bg_color = get_bg_color(lvl)
            annotations.append(f"<font backcolor='{bg_color}'><b>{w}</b></font> [{lvl}]")
            seen_words.add(w)

        right_text = "<br/>".join(annotations)

        rows.append([
            Paragraph(p_text, style_left),
            '',  # 中间留白列
            Paragraph(right_text, style_right),
        ])

    # 合并为单张表格（跨页自动拆分）
    table = Table(
        rows,
        colWidths=[LEFT_WIDTH, GAP_WIDTH, RIGHT_WIDTH],
        repeatRows=0
    )
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),       # 顶部对齐
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),   # 段落间距
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, -1), 0),
        ('LEFTPADDING', (2, 0), (2, -1), 0),
        ('RIGHTPADDING', (2, 0), (2, -1), 0),
    ]))

    doc.build([table], onFirstPage=_draw_decorations, onLaterPages=_draw_decorations)
    print(f"PDF 已成功生成: {output_pdf}")

# ================= 运行调用示例 =================
if __name__ == '__main__':
    TEXT_FILE = "article.txt"       # 英文文稿路径，默认同文件夹内
    VOCAB_FILE = "vocab.xlsx"       # 词汇表 Excel，其中A列单词，B列级别，可以自己加
    OUTPUT_PDF = "annotated.pdf"    # 输出PDF文件

    #  B 列含有中文（如 "高中"、"四级"），请指定中文字体路径：
    #  在Windows中如雅黑: "C:/Windows/Fonts/msyh.ttc"；
    #  在Mac中我不熟。
    FONT_PATH = "C:/Windows/Fonts/msyh.ttc"

    create_annotated_pdf(TEXT_FILE, VOCAB_FILE, OUTPUT_PDF, FONT_PATH)
