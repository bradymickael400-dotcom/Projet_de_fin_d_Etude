#!/usr/bin/env python3
"""Render the bilingual ARGOS reports in the supplied template structure."""

from pathlib import Path
import re

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS = ROOT / "docs" / "submissions"


def plain(text):
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def set_cell_margins(cell, top=45, start=55, bottom=45, end=55):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        from docx.oxml import OxmlElement
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def render(language):
    source = SUBMISSIONS / f"ARGOS_Template_{language}.md"
    lines = source.read_text(encoding="utf-8").splitlines()
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.38)
    section.bottom_margin = Inches(0.38)
    section.left_margin = Inches(0.43)
    section.right_margin = Inches(0.43)
    section.header_distance = Inches(0.18)
    section.footer_distance = Inches(0.18)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(7.6)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_after = Pt(1.7)
    normal.paragraph_format.line_spacing = 0.95
    for name, size in (("Heading 1", 10.5), ("Heading 2", 8.6), ("Heading 3", 8)):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(4 if name != "Heading 1" else 0)
        style.paragraph_format.space_after = Pt(1.5)
        style.paragraph_format.keep_with_next = True

    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        if not raw:
            i += 1
            continue
        if raw.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            rows = []
            for line in table_lines:
                cells = [plain(cell) for cell in line.strip("|").split("|")]
                if cells and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
                    continue
                rows.append(cells)
            if rows:
                table = doc.add_table(rows=0, cols=len(rows[0]))
                table.style = "Table Grid"
                table.autofit = True
                for row_index, values in enumerate(rows):
                    cells = table.add_row().cells
                    for cell, value in zip(cells, values):
                        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
                        set_cell_margins(cell)
                        cell.text = value
                        for paragraph in cell.paragraphs:
                            paragraph.paragraph_format.space_after = Pt(0)
                            paragraph.paragraph_format.line_spacing = 0.92
                            for run in paragraph.runs:
                                run.font.name = "Arial"
                                run.font.size = Pt(6.6 if row_index else 6.8)
                                run.font.bold = row_index == 0
                                run.font.color.rgb = RGBColor(0, 0, 0)
                doc.add_paragraph().paragraph_format.space_after = Pt(0)
            continue
        if raw.startswith("# "):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(plain(raw[2:]))
            run.bold = True
            run.font.name = "Arial"
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(0, 0, 0)
        elif raw.startswith("## "):
            doc.add_heading(plain(raw[3:]), level=2)
        elif raw.startswith("### "):
            doc.add_heading(plain(raw[4:]), level=3)
        elif raw.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Inches(0.15)
            p.paragraph_format.first_line_indent = Inches(-0.1)
            p.paragraph_format.space_after = Pt(0.7)
            p.add_run(plain(raw[2:]))
        elif re.match(r"^\d+\.\s", raw):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.16)
            p.paragraph_format.first_line_indent = Inches(-0.13)
            p.paragraph_format.space_after = Pt(0.7)
            p.add_run(plain(re.sub(r"^\d+\.\s", "", raw)))
        else:
            p = doc.add_paragraph(plain(raw))
            if raw.startswith("**"):
                p.paragraph_format.space_after = Pt(2)
        i += 1

    output = SUBMISSIONS / f"ARGOS_Template_Structure_{language}.docx"
    doc.save(output)
    return output


if __name__ == "__main__":
    for lang in ("FR", "EN"):
        print(render(lang))
