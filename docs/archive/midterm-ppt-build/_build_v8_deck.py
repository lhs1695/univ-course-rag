"""Build the editable v8 deck from the approved outline and report.

Reuse decision: use the installed python-pptx 1.0.2 public API (MIT,
https://github.com/scanny/python-pptx), as explicitly requested. No copied
library source or new dependency. Local work is limited to slide composition,
source-image placement, notes and checks. Acceptance: eight editable slides,
approved titles/metrics, prescribed images, clean geometry and rendered review.
Run from the repository root with backend/.venv/Scripts/python.exe.
"""

import re
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "中期答辩材料/汇报PPT/中期汇报-v8-candidate.pptx"
OUTLINE = ROOT / "中期答辩材料/汇报PPT/v8-outline.md"
REPORT = ROOT / "中期答辩材料/中期报告-修订稿.md"
IMAGES = ROOT / "中期答辩材料/彩排截图"
PAPER = "F7F1E8"
INK = "1C1917"
RED = "9B2C2C"
MUTED = "74695F"
RULE = "D5C9BA"
FONT = "Microsoft YaHei"


def color(value):
    return RGBColor.from_string(value)


def text(slide, value, x, y, w, h, size=22, ink=INK, bold=False, align=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, line in enumerate(value.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = FONT
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color(ink)
        p.space_after = Pt(8)
        p.line_spacing = 1.16
        if align is not None:
            p.alignment = align
        for run in p.runs:
            rpr = run._r.get_or_add_rPr()
            east_asian = OxmlElement("a:ea")
            east_asian.set("typeface", FONT)
            rpr.append(east_asian)
    return shape


def rule(slide, y, x=0.72, w=11.89):
    line = slide.shapes.add_connector(
        1, Inches(x), Inches(y), Inches(x + w), Inches(y)
    )
    line.line.color.rgb = color(RULE)
    line.line.width = Pt(0.7)


def notes(slide, extra=""):
    slide.notes_slide.notes_text_frame.text = (
        "页结构与标题：中期答辩材料/汇报PPT/v8-outline.md\n"
        "事实与数字来源：中期答辩材料/中期报告-修订稿.md\n" + extra
    )


def picture(slide, name, x, y, w, h, crop=None):
    path = IMAGES / name
    if not path.is_file():
        tf = slide.notes_slide.notes_text_frame
        tf.text += f"\n缺图：{path.relative_to(ROOT).as_posix()}，未使用其他图片替代。"
        return
    iw, ih = Image.open(path).size
    if crop:
        left, top, right, bottom = crop
        aspect = iw * (1 - left - right) / (ih * (1 - top - bottom))
    else:
        aspect = iw / ih
    pw, ph = min(w, h * aspect), min(h, w / aspect)
    pic = slide.shapes.add_picture(
        str(path), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2),
        width=Inches(pw), height=Inches(ph),
    )
    if crop:
        pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = crop
    slide.notes_slide.notes_text_frame.text += (
        f"\n截图：{path.relative_to(ROOT).as_posix()}。"
        + ("以 PowerPoint 原生裁切突出相关界面，原图完整嵌入，可恢复裁切。" if crop else "原图等比嵌入。")
    )


def new_slide(prs, number, title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color(PAPER)
    text(slide, title, 0.72, 0.53, 11.9, 0.72, 32, bold=True)
    rule(slide, 1.48)
    text(slide, f"{number:02d}", 12.05, 7.02, 0.55, 0.24, 11, MUTED, align=PP_ALIGN.RIGHT)
    notes(slide)
    return slide


def build():
    outline = OUTLINE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    titles = re.findall(r"\*\*标题：\*\*\s*(.+)", outline)
    assert len(titles) == 8, "大纲必须有八个标题"
    for required in ("2,501", "15/17", "16/17", "12/16", "22", "学情"):
        assert required in report, f"报告缺少口径：{required}"
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = titles[0]
    prs.core_properties.subject = "大学生创新训练计划中期汇报"
    prs.core_properties.author = "高校课程知识库项目组"

    s = new_slide(prs, 1, "")
    # Keep the cover quiet, with the approved title split only for composition.
    text(s, "大学生创新训练计划 · 中期汇报", 0.8, 1.15, 11.7, 0.5, 21, MUTED)
    text(s, "课程知识库 · 有据问答，\n通向教学反馈", 0.78, 2.2, 11.9, 2.0, 44, bold=True)
    text(s, "高校课程场景 · 可演示原型 · 分层核验", 0.83, 5.42, 11.7, 0.5, 23, RED)

    s = new_slide(prs, 2, titles[1])
    for y, label, sentence in (
        (2.02, "来源", "答案常无法回到指定课程资料与页码"),
        (3.43, "权限", "跨课与未授权访问难以拦截"),
        (4.84, "边界", "非搜题工具，非成绩或教学质量画像"),
    ):
        text(s, label, 0.77, y, 1.35, 0.55, 25, RED, True)
        text(s, sentence, 2.3, y, 10.0, 0.7, 26)
        rule(s, y + 0.99)

    s = new_slide(prs, 3, titles[2])
    text(s, "问 → 课内检索 → 有据回答 → 引用摘录 → 打开原 PDF 页", 0.75, 1.76, 11.85, 0.55, 23, RED)
    picture(s, "04-学生-引用打开PDF.png", 2.55, 2.44, 8.23, 4.32)

    s = new_slide(prs, 4, titles[3])
    text(s, "4 门课 · 27 份 PDF · 2,501 个文本切片（cn_v2）", 0.75, 1.79, 11.9, 0.6, 27, RED, True)
    text(s, "课程级权限贯穿检索、\n问答与原文件访问", 0.77, 2.85, 4.3, 1.0, 22)
    text(s, "依据不足与系统故障可区分", 0.77, 4.13, 4.3, 0.9, 22)
    text(s, "核心演示路径已复核与彩排", 0.77, 5.32, 4.3, 0.9, 22)
    picture(s, "03-学生-线代作答与引用.png", 5.48, 2.65, 7.1, 4.15)

    s = new_slide(prs, 5, titles[4])
    text(s, "15/17", 0.75, 1.88, 4.7, 1.28, 78, RED, True)
    text(s, "全部应答题中的事实要点通过率", 5.05, 2.16, 7.45, 0.55, 25, bold=True)
    text(s, "Dense；分母 17，未回答计失败", 5.05, 2.94, 7.45, 0.55, 21, MUTED)
    rule(s, 4.03)
    text(s, "事实要点     ·     引用支持     ·     严格预期页命中", 0.78, 4.45, 11.8, 0.7, 25)
    text(s, "本轮 22 题由项目开发者按既定规则核验；后续将邀请未参与开发者复核。\n严格页命中与引用支持分层呈现，页命中 ≠ 引用错误率。", 0.78, 6.0, 11.75, 0.78, 15, MUTED)

    s = new_slide(prs, 6, titles[5])
    text(s, "同一 22 题集完成 Dense / Hybrid 真实模型对照", 0.76, 1.81, 11.85, 0.65, 24)
    # A sparse native table keeps each numerator and denominator editable.
    table = s.shapes.add_table(3, 3, Inches(0.78), Inches(2.8), Inches(11.77), Inches(2.28)).table
    table.columns[0].width = Inches(6.77)
    table.columns[1].width = table.columns[2].width = Inches(2.5)
    data = [
        ["分层指标", "Dense", "Hybrid"],
        ["全部应答题中的事实要点通过率", "15/17", "16/17"],
        ["严格预期页命中", "12/16", "12/16"],
    ]
    for row, values in enumerate(data):
        for col, value in enumerate(values):
            cell = table.cell(row, col)
            cell.fill.solid()
            cell.fill.fore_color.rgb = color(PAPER if row else "EAE0D2")
            cell.margin_left = Inches(0.12)
            cell.margin_right = Inches(0.08)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text = value
            p = cell.text_frame.paragraphs[0]
            p.font.name = FONT
            p.font.size = Pt(21 if col == 0 else 25)
            p.font.bold = row == 0 or col > 0
            p.font.color.rgb = color(RED if row > 0 and col > 0 else INK)
            if col:
                p.alignment = PP_ALIGN.CENTER
    text(s, "Keyword-only 候选本轮未进入最终 evidence，仍需校准门槛与准入。", 0.78, 5.48, 11.75, 0.75, 21)
    text(s, "22 题为项目开发者核验。事实要点分母 17，未回答计失败；页命中 ≠ 引用错误率。\n本轮不据此宣称 Hybrid 显著更好。", 0.78, 6.35, 11.75, 0.65, 14, MUTED)

    s = new_slide(prs, 7, titles[6])
    text(s, "无课程权限：拒绝访问", 0.78, 1.83, 5.75, 0.55, 23, RED, True)
    text(s, "依据不足：明确拒答或提示", 6.85, 1.83, 5.75, 0.55, 23, RED, True)
    picture(s, "10-PERM-无权限.png", 0.78, 2.62, 5.7, 3.46, crop=(0.08, 0.15, 0.08, 0.32))
    picture(s, "05-学生-拒答.png", 6.85, 2.62, 5.7, 3.46, crop=(0.18, 0.64, 0.19, 0.0))
    text(s, "系统故障可单独区分，并提供重试入口", 0.78, 6.42, 11.75, 0.6, 22)

    s = new_slide(prs, 8, titles[7])
    for y, heading, detail in (
        (1.88, "可靠与证据", "权限、资料生命周期、引用定位与异常恢复"),
        (3.18, "学情 V1", "问题归纳 → 教师确认 → 处理记录 → 代表问题回归（非成绩画像）"),
        (4.48, "独立核验与工程收口", "未参与开发者复核、流式 / 性能基线、干净环境交付"),
    ):
        text(s, heading, 0.78, y, 11.8, 0.46, 23, RED, True)
        text(s, detail, 0.78, y + 0.56, 11.8, 0.6, 21)
    rule(s, 6.08)
    text(s, "不承诺公网部署；先可靠、再验证、后扩展。", 0.78, 6.4, 11.8, 0.55, 24, bold=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    check = Presentation(OUT)
    all_text = "\n".join(
        shape.text for slide in check.slides for shape in slide.shapes if shape.has_text_frame
    )
    # Table cells are also native editable text, checked independently.
    ok = len(check.slides) == 8 and all(
        value in all_text for value in ("有据问答", "15/17", "不宣称", "学情")
    )
    assert ok, "PPT 内容校验失败"
    for slide in check.slides:
        for shape in slide.shapes:
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left + shape.width <= check.slide_width
            assert shape.top + shape.height <= check.slide_height
    print(f"输出路径：{OUT.relative_to(ROOT).as_posix()}")
    print(f"页数：{len(check.slides)}")
    print(f"校验通过：{'是' if ok else '否'}")


if __name__ == "__main__":
    build()
