import os
import re
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. 配置级别与高亮底色的对应关系（支持 Hex 颜色码）
LEVEL_COLOR_MAP = {
    'A1': '#C8E6C9',  # 浅绿
    'A2': '#A5D6A7',  # 绿
    'B1': '#FFF59D',  # 浅黄
    'B2': '#FFE082',  # 橘黄
    'C1': '#FFAB91',  # 浅红/粉红
    'C2': '#F48FB1',  # 玫红
    
    # 国内教纲级别示例：
    '小学': '#D1C4E9', # 浅紫
    '初中': '#BBDEFB', # 浅蓝
    '高中': '#FFF59D', # 浅黄
    '四级': '#FFE082', # 橘黄
    '六级': '#FFAB91', # 浅红
}
DEFAULT_BG_COLOR = '#FFF59D'  # 默认底色（浅黄）

def get_bg_color(level_str):
    return LEVEL_COLOR_MAP.get(str(level_str).strip(), DEFAULT_BG_COLOR)

def create_annotated_pdf(text_file, vocab_file, output_pdf, font_path=None):
    """
    读取英文文本与Excel词汇表(A列单词, B列级别)，生成带背景高亮及右侧级别标注的PDF
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

    # 创建 PDF 文档模板 (A4，左右留边 30pt)
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    styles = getSampleStyleSheet()

    # 左侧英文段落样式 (占 2/3 宽)
    style_left = ParagraphStyle(
        name='EnglishStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=17,      # 行距
        alignment=4      # 两端对齐
    )

    # 右侧级别标注样式 (占 1/3 宽)
    style_right = ParagraphStyle(
        name='AnnotationStyle',
        parent=styles['Normal'],
        fontName=font_name_right,
        fontSize=9,
        leading=15,
        textColor=colors.HexColor('#424242')
    )

    elements = []
    # A4 页面可用总宽度为 535pt
    left_width = 355   # 左侧英文区约 2/3
    right_width = 180  # 右侧标注区约 1/3

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

        # 构建右侧注释（格式：单词 [级别]）
        annotations = []
        for w, lvl in found_in_paragraph.items():
            bg_color = get_bg_color(lvl)
            annotations.append(f"<font backcolor='{bg_color}'><b>{w}</b></font> [{lvl}]")

        right_text = "<br/>".join(annotations)

        # 组合为 2 列表格，保持左右并排及顶部对齐
        data = [[Paragraph(p_text, style_left), Paragraph(right_text, style_right)]]
        t = Table(data, colWidths=[left_width, right_width])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),          # 顶部对齐
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),      # 段落间距
        ]))
        elements.append(t)

    doc.build(elements)
    print(f"PDF 已成功生成: {output_pdf}")

# ================= 运行调用示例 =================
if __name__ == '__main__':
    TEXT_FILE = "article.txt"       # 英文文稿路径
    VOCAB_FILE = "vocab.xlsx"       # 词汇表 Excel (A列单词，B列级别)
    OUTPUT_PDF = "annotated.pdf"    # 输出文件路径
    
    # 若 B 列含有中文（如 "高中"、"四级"），请指定中文字体路径：
    # Windows 示例: "C:/Windows/Fonts/msyh.ttc"
    # Mac 示例: "/System/Library/Fonts/PingFang.ttc"
    FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
    
    create_annotated_pdf(TEXT_FILE, VOCAB_FILE, OUTPUT_PDF, FONT_PATH)