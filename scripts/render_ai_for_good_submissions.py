#!/usr/bin/env python3
"""Render the bilingual ARGOS competition briefs from their Markdown sources."""

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "submissions"
OUTPUT = SOURCE
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
TOKEN_RE = re.compile(r"(\*\*.*?\*\*|`[^`]+`)")


def add_hyperlink(paragraph, label, url):
    part = paragraph.part
    relationship = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "007C91")
    props.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    props.append(underline)
    run.append(props)
    text = OxmlElement("w:t")
    text.text = label
    run.append(text)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_inline(paragraph, value):
    cursor = 0
    for match in LINK_RE.finditer(value):
        add_plain_tokens(paragraph, value[cursor:match.start()])
        add_hyperlink(paragraph, match.group(1), match.group(2))
        cursor = match.end()
    add_plain_tokens(paragraph, value[cursor:])


def add_plain_tokens(paragraph, value):
    cursor = 0
    for match in TOKEN_RE.finditer(value):
        if match.start() > cursor:
            paragraph.add_run(value[cursor:match.start()])
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        else:
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(50, 70, 80)
        cursor = match.end()
    if cursor < len(value):
        paragraph.add_run(value[cursor:])


def set_cell_shading(cell, fill):
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def render(source_path):
    lines = source_path.read_text(encoding="utf-8").splitlines()
    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.52)
    section.bottom_margin = Inches(0.48)
    section.left_margin = Inches(0.62)
    section.right_margin = Inches(0.62)
    section.header_distance = Inches(0.22)
    section.footer_distance = Inches(0.22)

    normal = document.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(8.7)
    normal.font.color.rgb = RGBColor(37, 50, 61)
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1.03
    for style_name, size in (("Heading 1", 14), ("Heading 2", 10.4), ("Heading 3", 9.2)):
        style = document.styles[style_name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 95, 112)
        style.paragraph_format.space_before = Pt(7 if style_name != "Heading 1" else 0)
        style.paragraph_format.space_after = Pt(3)
        style.paragraph_format.keep_with_next = True

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header.add_run("ARGOS  ·  AI FOR GOOD SANDBOX HACKATHON  ·  29 OCTOBER 2026")
    header_run.font.name = "Aptos"
    header_run.font.size = Pt(7)
    header_run.font.color.rgb = RGBColor(105, 120, 130)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("ARGOS · Technical submission · ").font.size = Pt(7)
    page = OxmlElement("w:fldSimple")
    page.set(qn("w:instr"), "PAGE")
    footer._p.append(page)

    first_heading = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            paragraph = document.add_paragraph(style="Title")
            paragraph.paragraph_format.space_after = Pt(5)
            paragraph.paragraph_format.keep_with_next = True
            run = paragraph.add_run(stripped[2:])
            run.font.name = "Aptos Display"
            run.font.size = Pt(15)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 69, 84)
            first_heading = False
        elif stripped.startswith("## "):
            document.add_heading(stripped[3:], level=2)
        elif stripped.startswith("- "):
            paragraph = document.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.left_indent = Inches(0.18)
            paragraph.paragraph_format.first_line_indent = Inches(-0.12)
            paragraph.paragraph_format.space_after = Pt(2)
            add_inline(paragraph, stripped[2:])
        elif re.match(r"^\d+\.\s", stripped):
            paragraph = document.add_paragraph(style="List Number")
            paragraph.paragraph_format.left_indent = Inches(0.2)
            paragraph.paragraph_format.first_line_indent = Inches(-0.14)
            paragraph.paragraph_format.space_after = Pt(2)
            add_inline(paragraph, re.sub(r"^\d+\.\s", "", stripped))
        else:
            paragraph = document.add_paragraph()
            if stripped.startswith("**") and " · **" in stripped:
                paragraph.paragraph_format.space_after = Pt(5)
                paragraph.paragraph_format.keep_with_next = True
            add_inline(paragraph, stripped)

    target = OUTPUT / f"{source_path.stem}.docx"
    document.save(target)
    return target


if __name__ == "__main__":
    for language in ("FR", "EN"):
        source = SOURCE / f"ARGOS_AI_for_Good_{language}.md"
        print(render(source))
