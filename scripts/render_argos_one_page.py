#!/usr/bin/env python3
"""Create compact French and English ARGOS project briefs from Markdown."""

from pathlib import Path
import re

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS = ROOT / "docs" / "submissions"


def clean(text):
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def render(lang):
    lines = (SUBMISSIONS / f"ARGOS_One_Page_{lang}.md").read_text(encoding="utf-8").splitlines()
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.38)
    section.bottom_margin = Inches(0.38)
    section.left_margin = Inches(0.48)
    section.right_margin = Inches(0.48)
    section.header_distance = Inches(0.16)
    section.footer_distance = Inches(0.16)

    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.2)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_after = Pt(2.5)
    normal.paragraph_format.line_spacing = 0.96
    for name, size in (("Heading 1", 16), ("Heading 2", 10.2)):
        style = doc.styles[name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(4 if name == "Heading 2" else 0)
        style.paragraph_format.space_after = Pt(1.5)
        style.paragraph_format.keep_with_next = True

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|"):
            raw_rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw_rows.append(lines[i].strip())
                i += 1
            rows = []
            for raw in raw_rows:
                values = [clean(cell) for cell in raw.strip("|").split("|")]
                if values and all(re.fullmatch(r":?-{3,}:?", v.replace(" ", "")) for v in values):
                    continue
                rows.append(values)
            if rows:
                table = doc.add_table(rows=0, cols=len(rows[0]))
                table.style = "Table Grid"
                table.autofit = False
                if len(rows[0]) == 2:
                    table.columns[0].width = Inches(1.7)
                    table.columns[1].width = Inches(5.6)
                for ridx, values in enumerate(rows):
                    cells = table.add_row().cells
                    for col_index, (cell, value) in enumerate(zip(cells, values)):
                        if len(rows[0]) == 2:
                            cell.width = Inches(1.7 if col_index == 0 else 5.6)
                        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                        cell.text = value
                        for p in cell.paragraphs:
                            p.paragraph_format.space_after = Pt(0)
                            p.paragraph_format.line_spacing = 0.92
                            for run in p.runs:
                                run.font.name = "Aptos"
                                run.font.size = Pt(8.5)
                                run.bold = ridx == 0
                                run.font.color.rgb = RGBColor(0, 0, 0)
                doc.add_paragraph().paragraph_format.space_after = Pt(0)
            continue
        if line.startswith("# "):
            p = doc.add_paragraph(style="Heading 1")
            p.add_run(clean(line[2:]))
        elif line.startswith("## "):
            doc.add_heading(clean(line[3:]), level=2)
        elif line.startswith("**"):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(clean(line))
            run.bold = True
            run.font.color.rgb = RGBColor(0, 0, 0)
            run.font.size = Pt(8.8)
        else:
            doc.add_paragraph(clean(line))
        i += 1

    target = SUBMISSIONS / f"ARGOS_One_Page_{lang}.docx"
    doc.save(target)
    return target


if __name__ == "__main__":
    for language in ("FR", "EN"):
        print(render(language))
