"""Generation de rapports PDF simples sans dependance externe."""

from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import hashlib
import json
import re

from sqlalchemy import text

from app.extensions import db


BRAND_NAVY = (0.055, 0.118, 0.220)
BRAND_BLUE = (0.055, 0.345, 0.620)
BRAND_CYAN = (0.000, 0.690, 0.780)
BRAND_LIGHT = (0.940, 0.965, 0.980)
BRAND_TEXT = (0.110, 0.145, 0.190)
CONTRACT_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "CONTRAT_DE_PRESTATION_DE_SERVICES_DE_TRACABILITE_ET_DE_SECURISATION.docx"


class ProfessionalPDF:
    """Petit moteur PDF vectoriel autonome, sans dependance binaire."""

    def __init__(self, title="ARGOS"):
        self.title = title
        self.pages = []
        self._ops = []
        self.page_width = 595
        self.page_height = 842
        self._images = {}

    @staticmethod
    def _color(color):
        return " ".join(f"{v:.3f}" for v in color)

    def text(self, x, y, value, size=10, bold=False, color=BRAND_TEXT):
        font = "F2" if bold else "F1"
        safe = _pdf_escape(value).encode("latin-1", "replace").decode("latin-1")
        self._ops.append(
            f"BT /{font} {size} Tf {self._color(color)} rg 1 0 0 1 {x:.2f} {y:.2f} Tm ({safe}) Tj ET"
        )

    def line(self, x1, y1, x2, y2, color=(0.75, 0.78, 0.82), width=0.6):
        self._ops.append(
            f"{self._color(color)} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
        )

    def rect(self, x, y, width, height, fill=None, stroke=(0.75, 0.78, 0.82), line_width=0.6):
        if fill is not None:
            self._ops.append(f"{self._color(fill)} rg {x} {y} {width} {height} re f")
        if stroke is not None:
            self._ops.append(
                f"{self._color(stroke)} RG {line_width:.2f} w {x} {y} {width} {height} re S"
            )

    def jpeg(self, x, y, width, height, data):
        """Ajoute une image JPEG comme ressource PDF, sans dépendance externe."""
        name = f"Im{len(self._images) + 1}"
        image_width, image_height = _jpeg_dimensions(data)
        self._images[name] = (data, image_width, image_height)
        self._ops.append(f"q {width:.2f} 0 0 {height:.2f} {x:.2f} {y:.2f} cm /{name} Do Q")

    def brand_header(self, document_type, reference="", include_contract_logo=False):
        self.rect(0, 766, self.page_width, 76, fill=BRAND_NAVY, stroke=None)
        logo = _contract_logo() if include_contract_logo else None
        if logo:
            self.jpeg(36, 776, 108, 59, logo)
        else:
            self.text(36, 801, "ARGOS", 21, True, (1, 1, 1))
        self.text(390, 807, document_type.upper(), 11, True, (1, 1, 1))
        if reference:
            self.text(390, 789, reference, 8, False, (0.75, 0.88, 0.96))

    def footer(self, page_number):
        self.line(36, 37, 559, 37, BRAND_CYAN, 1.2)
        self.text(36, 22, "ARGOS - Document confidentiel", 7, False, (0.35, 0.40, 0.46))
        self.text(475, 22, f"Page {page_number}", 7, False, (0.35, 0.40, 0.46))

    def finish_page(self):
        self.footer(len(self.pages) + 1)
        self.pages.append("\n".join(self._ops))
        self._ops = []

    def render(self):
        if self._ops or not self.pages:
            self.finish_page()
        objects = []

        def add(body):
            objects.append(body)
            return len(objects)

        font_regular = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        font_bold = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        image_refs = {}
        for name, (data, width, height) in self._images.items():
            stream = data.decode("latin-1")
            image_refs[name] = add(
                f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>\n"
                f"stream\n{stream}\nendstream"
            )
        xobjects = " ".join(f"/{name} {ref} 0 R" for name, ref in image_refs.items())
        page_refs = []
        for stream in self.pages:
            encoded = stream.encode("latin-1", "replace")
            content_ref = add(f"<< /Length {len(encoded)} >>\nstream\n{stream}\nendstream")
            page_ref = add(
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {self.page_width} {self.page_height}] "
                f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> "
                f"/XObject << {xobjects} >> >> "
                f"/Contents {content_ref} 0 R >>"
            )
            page_refs.append(page_ref)
        kids = " ".join(f"{ref} 0 R" for ref in page_refs)
        pages_ref = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>")
        catalog_ref = add(f"<< /Type /Catalog /Pages {pages_ref} 0 R >>")
        objects = [obj.replace("/Parent 0 0 R", f"/Parent {pages_ref} 0 R") for obj in objects]

        chunks = ["%PDF-1.4\n%ARGOS\n"]
        offsets = [0]
        for index, body in enumerate(objects, 1):
            offsets.append(sum(len(c.encode("latin-1", "replace")) for c in chunks))
            chunks.append(f"{index} 0 obj\n{body}\nendobj\n")
        xref = sum(len(c.encode("latin-1", "replace")) for c in chunks)
        chunks.append(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n")
        chunks.extend(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
        chunks.append(
            f"trailer\n<< /Size {len(objects)+1} /Root {catalog_ref} 0 R >>\nstartxref\n{xref}\n%%EOF\n"
        )
        return "".join(chunks).encode("latin-1", "replace")


def _jpeg_dimensions(data):
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in range(0xC0, 0xC4):
            return int.from_bytes(data[index + 7:index + 9], "big"), int.from_bytes(data[index + 5:index + 7], "big")
        if index + 4 > len(data):
            break
        index += 2 + int.from_bytes(data[index + 2:index + 4], "big")
    raise ValueError("Dimensions JPEG introuvables")


def _contract_logo():
    try:
        with ZipFile(CONTRACT_TEMPLATE_PATH) as archive:
            images = sorted(name for name in archive.namelist() if name.startswith("word/media/") and name.lower().endswith((".jpg", ".jpeg")))
            return archive.read(images[0]) if images else None
    except Exception:
        return None


def _draw_wrapped(pdf, x, y, value, width_chars=86, line_height=13, size=9, bold=False):
    for line_value in _wrap(value, width_chars):
        pdf.text(x, y, line_value, size, bold)
        y -= line_height
    return y


def generate_inventory_pdf(inventory):
    """Genere la feuille d'inventaire ARGOS inspiree du modele fourni."""
    reference = inventory.get("sheet_number") or inventory.get("reference") or "INV-BROUILLON"
    pdf = ProfessionalPDF(f"Inventaire {reference}")
    pdf.brand_header("Feuille d'inventaire", reference)
    pdf.text(36, 735, "INVENTAIRE", 25, True, BRAND_NAVY)
    metadata = [
        ("Feuille n°", reference),
        ("Réalisé par", inventory.get("prepared_by") or "ARGOS"),
        ("Rayon / expédition", inventory.get("department") or inventory.get("shipment") or "Logistique"),
        ("Date", inventory.get("date") or datetime.now(timezone.utc).strftime("%d/%m/%Y")),
        ("Conteneur", inventory.get("container_id") or "Non attribué"),
        ("Destination", inventory.get("destination") or "Non renseignée"),
    ]
    y = 706
    for label, value in metadata:
        pdf.rect(36, y - 4, 523, 20, fill=BRAND_LIGHT)
        pdf.text(45, y + 2, label.upper(), 7, True, BRAND_BLUE)
        pdf.text(172, y + 2, value, 9, False)
        y -= 24

    columns = [
        ("REFERENCE", 78), ("NOM DE L'ARTICLE", 125), ("DESCRIPTION", 145),
        ("QUANTITE", 61), ("P.U.", 52), ("VALEUR", 62),
    ]
    table_x, table_y, row_h = 36, 540, 24
    x = table_x
    for title, width in columns:
        pdf.rect(x, table_y, width, row_h, fill=BRAND_NAVY, stroke=(1, 1, 1))
        pdf.text(x + 4, table_y + 8, title, 6.5, True, (1, 1, 1)) # type: ignore
        x += width

    items = inventory.get("items") or []
    total = 0.0
    for row_index in range(16):
        item = items[row_index] if row_index < len(items) else {}
        quantity = float(item.get("quantity") or 0)
        unit_price = float(item.get("unit_price") or 0)
        value = quantity * unit_price
        total += value
        values = [
            item.get("reference", ""), item.get("name", ""), item.get("description", ""),
            f"{quantity:g}" if item else "", f"{unit_price:,.0f}" if item else "",
            f"{value:,.0f}" if item else "",
        ]
        y = table_y - row_h * (row_index + 1)
        x = table_x
        fill = (0.975, 0.985, 0.992) if row_index % 2 else (1, 1, 1)
        for (_, width), value_text in zip(columns, values):
            pdf.rect(x, y, width, row_h, fill=fill)
            pdf.text(x + 4, y + 8, value_text, 7, False)
            x += width
    total_y = table_y - row_h * 17
    pdf.rect(36, total_y, 523, 28, fill=BRAND_NAVY, stroke=None)
    pdf.text(390, total_y + 10, "VALEUR TOTALE", 8, True, (1, 1, 1))
    pdf.text(500, total_y + 10, f"{total:,.0f} {inventory.get('currency', 'XAF')}", 8, True, (1, 1, 1))
    pdf.text(36, 78, "Validation", 9, True, BRAND_BLUE)
    pdf.line(36, 58, 210, 58)
    pdf.text(385, 78, "Visa du responsable", 9, True, BRAND_BLUE)
    pdf.line(385, 58, 559, 58)
    return pdf.render()


def generate_contract_pdf(contract):
    """Genere un contrat ARGOS a partir du modele de prestation fourni."""
    number = contract.get("contract_number") or "CTR-BROUILLON"
    pdf = ProfessionalPDF(f"Contrat {number}")
    pdf.brand_header("Contrat de services", number, include_contract_logo=True)

    paragraphs = _contract_template_paragraphs()
    replacements = _contract_replacements(contract)
    rendered = [_replace_contract_placeholders(paragraph, replacements) for paragraph in paragraphs]

    y = 738
    for index, paragraph in enumerate(rendered):
        is_title = index == 0
        is_article = paragraph.lower().startswith("article ")
        is_signature = paragraph.strip().lower() == "signatures"
        size = 13 if is_title else (10.5 if is_article or is_signature else 8.5)
        bold = is_title or is_article or is_signature or paragraph in {"Entre les soussignés :", "D’une part,", "Et d’autre part,"}
        width = 70 if is_title else 90
        line_height = 15 if is_title else 11
        required = 18 + len(_wrap(paragraph, width)) * line_height
        if y - required < 70:
            pdf.finish_page()
            pdf.brand_header("Contrat de services", number, include_contract_logo=True)
            y = 735
        if is_article:
            pdf.rect(36, y - 3, 523, 17, fill=BRAND_LIGHT, stroke=None)
            pdf.text(45, y + 2, paragraph, size, True, BRAND_NAVY) # pyright: ignore[reportArgumentType]
            y -= 22
        else:
            y = _draw_wrapped(pdf, 36, y, paragraph, width, line_height, size, bold) # pyright: ignore[reportArgumentType]
            y -= 6 if is_title else 3

    if y < 180:
        pdf.finish_page()
        pdf.brand_header("Contrat de services", number, include_contract_logo=True)
        y = 730
    pdf.rect(36, y - 104, 250, 100, fill=BRAND_LIGHT)
    pdf.rect(309, y - 104, 250, 100, fill=BRAND_LIGHT)
    pdf.text(48, y - 24, "POUR ARGOS", 9, True, BRAND_BLUE)
    pdf.text(321, y - 24, "POUR L’ENTREPRISE", 9, True, BRAND_BLUE)
    pdf.text(48, y - 47, contract.get("argos_signer") or "Direction générale ARGOS", 9, False)
    pdf.text(321, y - 47, contract.get("company_signer") or "Signature en attente", 9, False)
    pdf.text(48, y - 80, f"Date : {contract.get('argos_signed_at') or '---'}", 8, False)
    pdf.text(321, y - 80, f"Date : {contract.get('company_signed_at') or '---'}", 8, False)
    result = pdf.render()
    return result


def _contract_template_paragraphs():
    if not CONTRACT_TEMPLATE_PATH.exists():
        return [
            "CONTRAT DE PRESTATION DE SERVICES DE TRACABILITE ET DE SECURISATION DES CONTENEURS",
            "Référence du contrat : [N° / identifiant du client]",
            "Le présent contrat encadre la mise à disposition et l'exploitation des services ARGOS.",
        ]
    try:
        with ZipFile(CONTRACT_TEMPLATE_PATH) as archive:
            xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for node in root.findall(".//w:p", ns):
            text_value = "".join((text_node.text or "") for text_node in node.findall(".//w:t", ns)).strip()
            if text_value:
                paragraphs.append(text_value)
        return paragraphs
    except Exception:
        return [
            "CONTRAT DE PRESTATION DE SERVICES DE TRACABILITE ET DE SECURISATION DES CONTENEURS",
            "Référence du contrat : [N° / identifiant du client]",
            "Le présent contrat encadre la mise à disposition et l'exploitation des services ARGOS.",
        ]


def _contract_replacements(contract):
    terms = contract.get("terms") or {}
    if isinstance(terms, str):
        try:
            terms = json.loads(terms)
        except Exception:
            terms = {}
    starts_on = contract.get("starts_on") or "---"
    ends_on = contract.get("ends_on") or "---"
    months = terms.get("contract_months") or contract.get("contract_months") or "---"
    location = terms.get("location") or contract.get("location") or "---"
    lat = terms.get("lat")
    lon = terms.get("lon")
    position = location
    if lat not in (None, "") and lon not in (None, ""):
        position = f"{location} (lat {lat}, lon {lon})"
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    return {
        "[N° / identifiant du client]": contract.get("contract_number") or "---",
        "[JJ/MM/AAAA]": today,
        "[Ville, Pays]": location,
        "[Ville]": location,
        "[Nom de l’entreprise]": contract.get("company_name") or "---",
        "[niu]": terms.get("niu") or contract.get("niu") or "---",
        "[utilise les donnee long et lat pour determier la position]": position,
        "[login]": terms.get("login") or contract.get("login") or "---",
        "[fonction]": "Representant legal",
        "[XXXXX]": "à compléter",
        "[Ville/site du Client]": location,
        "[date de debut du contrat]": starts_on,
        "[0 FCFA]": "0 FCFA",
        "[60% du prix d’expédition du conteneur]": "60% du prix d'expedition du conteneur",
        "[recuper dans le formulaire mois]": f"{months} mois",
        "[A déterminer]": f"du {starts_on} au {ends_on}",
        "[X mois]": f"{months} mois",
        "[X années]": "5 annees",
        "[Prestataire / Client]": "Prestataire",
    }


def _replace_contract_placeholders(text_value, replacements):
    rendered = str(text_value or "")
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, str(value))
    return rendered


def _pdf_escape(value):
    value = "" if value is None else str(value)
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(text_value, width=88):
    words = re.split(r"\s+", str(text_value or "").strip())
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            if current:
                lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines or [""]


def build_text_pdf(title, sections):
    """Construit un rapport ARGOS pagine et lisible."""
    pdf = ProfessionalPDF(title)
    reference = hashlib.sha256(f"{title}|{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12].upper()
    pdf.brand_header("Rapport opérationnel", reference)
    pdf.text(36, 730, title.upper(), 19, True, BRAND_NAVY)
    pdf.text(36, 708, f"Généré le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC", 8, False, BRAND_BLUE)
    y = 675
    for heading, content in sections:
        items = content if isinstance(content, (list, tuple)) else [content]
        estimated_lines = sum(max(1, len(_wrap(item, 88))) for item in items)
        if y - (estimated_lines * 13 + 35) < 60:
            pdf.finish_page()
            pdf.brand_header("Rapport opérationnel", reference)
            y = 730
        pdf.rect(36, y - 5, 523, 22, fill=BRAND_LIGHT, stroke=None)
        pdf.text(45, y + 2, heading.upper(), 9, True, BRAND_BLUE)
        y -= 25
        for item in items:
            if y < 60:
                pdf.finish_page()
                pdf.brand_header("Rapport opérationnel", reference)
                y = 730
            y = _draw_wrapped(pdf, 48, y, item, 86, 13, 8.5) # pyright: ignore[reportArgumentType]
            y -= 5
        y -= 8
    pdf.text(36, 50, f"Référence de vérification : {reference}", 7, False, (0.35, 0.40, 0.46))
    return pdf.render()


def collect_container_report(container_id):
    box = db.session.execute(text("""
        SELECT b.id_boite, b.numero_serie, b.id_conteneurs, b.id_proprietaire,
               p.nom_agence, d.device_uid
        FROM boite_noir b
        LEFT JOIN proprietaire_conteneur p ON p.id = b.id_proprietaire
        LEFT JOIN black_box_devices bbd ON bbd.black_box_id = b.id_boite AND bbd.status = 'ACTIVE'
        LEFT JOIN iot_devices d ON d.id = bbd.device_id
        WHERE b.id_conteneurs = :container_id
        ORDER BY b.created_at DESC NULLS LAST
        LIMIT 1
    """), {"container_id": container_id}).fetchone()

    events = db.session.execute(text("""
        SELECT COALESCE(horodatage, created_at) AS ts, log_action, temperature,
               humidite, pressions, chocs, vitesse, lat, lon, notif
        FROM evenement_save
        WHERE id_boite = :box_id
        ORDER BY COALESCE(horodatage, created_at)
        LIMIT 500
    """), {"box_id": box.id_boite if box else None}).fetchall()

    event_lines = []
    for event in events:
        alerts = ""
        if event.notif:
            try:
                parsed = json.loads(event.notif)
                alerts = f" | Alertes: {', '.join(parsed)}" if parsed else ""
            except Exception:
                alerts = f" | Alertes: {event.notif}"
        event_lines.append(
            f"{event.ts} - {event.log_action or 'Evenement'} "
            f"T={event.temperature} H={event.humidite} P={event.pressions} "
            f"Choc={event.chocs} V={event.vitesse} GPS=({event.lat},{event.lon}){alerts}"
        )

    return {
        "title": f"Rapport conteneur {container_id}",
        "sections": [
            ("Entreprise", box.nom_agence if box else "Non rattachee"),
            ("Conteneur", container_id),
            ("Boite noire", f"{box.id_boite} / {box.numero_serie}" if box else "Aucune boite active"),
            ("Prototype ESP32", box.device_uid if box and box.device_uid else "Non lie"),
            ("Evenements chronologiques", event_lines or ["Aucun evenement enregistre"]),
            ("Synthese", "Rapport genere depuis les donnees autorisees disponibles dans ARGOS."),
        ],
    }


def generate_container_report_pdf(container_id):
    report = collect_container_report(container_id)
    return build_text_pdf(report["title"], report["sections"])
