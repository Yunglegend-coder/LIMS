"""Shared report content and downloadable PDF/DOCX renderers."""

from html import escape
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from PIL import Image as PILImage
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Image as ReportImage,
    Spacer,
    Table,
    TableStyle,
)

from assays.models import AssayOrder, AssayStatus
from .models import SampleReport


LAB_NAME = "KADUNA POULTRY DISEASE DIAGNOSTIC LABORATORY"
LAB_ADDRESS = "NO. 1, KUBANI CRESCENT, BARNAWA, KADUNA"
LAB_EMAIL = "kadunapoultrylab@gmail.com"
LOGO_PATH = Path(settings.BASE_DIR) / "modification" / "logo.jpg"


def _read_image(file_field):
    if not file_field:
        return None
    try:
        file_field.open("rb")
        return file_field.read()
    except (OSError, ValueError):
        return None


def _normalize_image(image_bytes):
    if not image_bytes:
        return None
    try:
        with PILImage.open(BytesIO(image_bytes)) as image:
            image.load()
            image_format = image.format
            if image_format not in {"JPEG", "PNG"}:
                return None
            output = BytesIO()
            image.save(output, format=image_format)
            return {
                "data": output.getvalue(),
                "extension": "jpg" if image_format == "JPEG" else "png",
                "width": image.width,
                "height": image.height,
            }
    except (OSError, ValueError):
        return None


def _lab_logo():
    try:
        return _normalize_image(LOGO_PATH.read_bytes())
    except OSError:
        return None


def _user_signature(user):
    if not user:
        return None
    try:
        return _normalize_image(_read_image(user.profile.signature))
    except (AttributeError, ObjectDoesNotExist, ValueError):
        return None


def format_necropsy_findings(report=None):
    if report and report.carcass_count is not None:
        lines = [f"Number of carcasses examined: {report.carcass_count}"]
        findings = list(
            report.pathology_findings.select_related("finding").all()
        )
        if findings:
            lines.extend(
                f"{entry.finding.name} ({entry.carcass_count}/{report.carcass_count})"
                for entry in findings
            )
        else:
            lines.append("No gross pathologies recorded.")
        return "\n".join(lines)
    return ""


def build_report_data(sample, report=None, exporting_user=None):
    customer = sample.farm.customer if sample.farm_id else None
    clinical_details = []
    for label, value in (
        ("Age", sample.age),
        ("Breed/Species", sample.breed_species),
        ("Source of Birds", sample.source_of_birds),
        ("Feed", sample.feed_type),
        ("Population", sample.population),
        ("Water Source", sample.source_of_water),
        ("Housing", sample.housing),
        ("Major Complaint", sample.major_complaint),
        ("Mortality pattern", sample.mortality_pattern),
        ("Medication", sample.medication),
        ("Vaccination History", sample.vaccination_history),
        ("Drugs", sample.drugs),
        ("Vaccination", sample.vaccination),
        ("Last vaccination date", sample.last_vaccination),
    ):
        if value:
            clinical_details.append((label, str(value)))

    orders = (
        AssayOrder.objects.filter(
            sample=sample,
            status=AssayStatus.COMPLETED,
            result__isnull=False,
            assay__is_biochemical=False,
            assay__is_client_visible=True,
        )
        .select_related(
            "assay",
            "result",
            "result__performed_by",
            "result__binary_result",
            "result__gram_result",
            "result__ast_result",
            "result__ndhi_result",
            "result__pcr_result",
            "result__tsi_result",
            "result__culture_result",
            "result__count_result",
        )
        .prefetch_related(
            "result__ast_result__items__antibiotic",
        )
        .order_by("assay__laboratory_section", "assay__name")
    )

    assay_results = []
    for order in orders:
        result = order.result
        performer = result.performed_by
        assay_label = order.assay.name
        if order.doc_subtype:
            assay_label = f"{assay_label} — {order.get_doc_subtype_display()}"
        item = {
            "assay": assay_label,
            "rows": [],
            "table": [],
            "remarks": result.remarks,
            "performed_by": (
                performer.get_full_name() or performer.username
                if performer else "Not recorded"
            ),
        }
        if hasattr(result, "ast_result"):
            item["table"] = [
                (entry.antibiotic.name, entry.get_interpretation_display())
                for entry in result.ast_result.items.all()
            ]
        elif hasattr(result, "culture_result"):
            culture = result.culture_result
            item["rows"] = [("Growth", culture.get_growth_display())]
            if culture.organism_name:
                item["rows"].append(("Organism identified", culture.organism_name))
            if culture.colony_description:
                item["rows"].append(("Colony description", culture.colony_description))
            if culture.identification_notes:
                item["rows"].append(("Identification notes", culture.identification_notes))
        elif hasattr(result, "binary_result"):
            item["rows"] = [("Result", result.binary_result.get_result_display())]
        elif hasattr(result, "gram_result"):
            item["rows"] = [("Result", result.gram_result.get_result_display())]
        elif hasattr(result, "tsi_result"):
            item["rows"] = [("Result", result.tsi_result.get_result_display())]
        elif hasattr(result, "count_result"):
            count_result = result.count_result
            item["rows"] = [("Count", f"{count_result.count} {count_result.unit}")]
        elif hasattr(result, "ndhi_result"):
            item["rows"] = [("Result", result.ndhi_result.result)]
        elif hasattr(result, "pcr_result"):
            pcr = result.pcr_result
            item["rows"] = [
                ("Target", pcr.target),
                ("Result", pcr.result),
            ]
            if pcr.cq_ct is not None:
                item["rows"].append(("Cq / Ct", str(pcr.cq_ct)))
            if pcr.interpretation:
                item["rows"].append(("Interpretation", pcr.interpretation))
        else:
            continue
        assay_results.append(item)

    if report is None:
        try:
            report = sample.report
        except SampleReport.DoesNotExist:
            report = None
    return {
        "lab_name": LAB_NAME,
        "lab_address": LAB_ADDRESS,
        "lab_email": LAB_EMAIL,
        "client": customer.name if customer else "—",
        "farm": sample.farm.name if sample.farm_id else "",
        "date": sample.received_date,
        "case_code": sample.case_code,
        "sample_type": sample.get_sample_type_full_display(),
        "clinical_details": clinical_details,
        "pathology": format_necropsy_findings(report),
        "clinical_diagnosis": report.clinical_diagnosis if report else "",
        "laboratory_diagnosis": report.laboratory_diagnosis if report else "",
        "isolate": report.isolate if report else "",
        "assay_results": assay_results,
        "comments": report.comments_recommendations if report else "",
        "exported_by": (
            exporting_user.get_full_name() or exporting_user.username
            if exporting_user else "Authorized Laboratory Officer"
        ),
    }


def _pdf_paragraph(text, style, *, markup=False):
    safe = str(text or "—") if markup else escape(str(text or "—"))
    safe = safe.replace("\n", "<br/> ")
    return Paragraph(safe, style)


def pdf_response(sample, report=None, exporting_user=None):
    data = build_report_data(sample, report, exporting_user=exporting_user)
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="LabTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=14, leading=17, spaceAfter=4))
    styles.add(ParagraphStyle(name="LabContact", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=11, leading=14, spaceBefore=12, spaceAfter=5, textColor=colors.HexColor("#1e3a5f")))
    styles.add(ParagraphStyle(name="BodyReport", parent=styles["BodyText"], fontSize=9.5, leading=14, spaceAfter=4))

    story = []
    logo = _lab_logo()
    if logo:
        story.append(ReportImage(
            BytesIO(logo["data"]),
            width=34 * mm,
            height=25 * mm,
            kind="proportional",
        ))
    story.extend([
        _pdf_paragraph(data["lab_name"], styles["LabTitle"]),
        _pdf_paragraph(data["lab_address"], styles["LabContact"]),
        _pdf_paragraph(data["lab_email"], styles["LabContact"]),
        Spacer(1, 8),
    ])
    meta = [
        ["CLIENT", data["client"], "DATE", data["date"].strftime("%B %d, %Y")],
        ["CASE NO.", data["case_code"], "SAMPLE", data["sample_type"]],
    ]
    meta_table = Table(meta, colWidths=[24 * mm, 64 * mm, 20 * mm, 60 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eef5")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#e8eef5")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b9c4d0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([meta_table, Spacer(1, 12), _pdf_paragraph("Dear Sir/Ma,", styles["BodyReport"]),
                  _pdf_paragraph(f"Find below the result of {escape(data['sample_type'])} analysis carried out on the sample submitted for laboratory investigation.", styles["BodyReport"])])

    def section(title, body):
        story.append(_pdf_paragraph(title, styles["Section"]))
        story.append(_pdf_paragraph(body, styles["BodyReport"]))

    if data["clinical_details"]:
        story.append(_pdf_paragraph("Flock and Clinical History", styles["Section"]))
        for label, value in data["clinical_details"]:
            story.append(_pdf_paragraph(f"<b>{escape(str(label))}:</b> {escape(str(value)).replace(chr(10), '<br/>')}", styles["BodyReport"], markup=True))
    if data["pathology"]:
        section("Necropsy Findings", data["pathology"])
    if data["clinical_diagnosis"]:
        section("Clinical Diagnosis", data["clinical_diagnosis"])
    if data["laboratory_diagnosis"]:
        section("Laboratory Diagnosis", data["laboratory_diagnosis"])
    if data["isolate"]:
        section("Isolate", data["isolate"])
    for assay in data["assay_results"]:
        story.append(_pdf_paragraph(assay["assay"], styles["Section"]))
        story.append(_pdf_paragraph(f"Entered by: {assay['performed_by']}", styles["BodyReport"]))
        if assay["table"]:
            table = Table([["Antimicrobial", "Interpretation"]] + [list(row) for row in assay["table"]], colWidths=[90 * mm, 78 * mm], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b9c4d0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(table)
        else:
            for label, value in assay["rows"]:
                story.append(_pdf_paragraph(f"<b>{escape(str(label))}:</b> {escape(str(value)).replace(chr(10), '<br/>')}", styles["BodyReport"], markup=True))
        if assay["remarks"]:
            story.append(_pdf_paragraph(f"<b>Remarks:</b> {escape(assay['remarks']).replace(chr(10), '<br/>')}", styles["BodyReport"], markup=True))
    if data["comments"]:
        section("Comments and Recommendations", data["comments"])
    story.extend([Spacer(1, 18), _pdf_paragraph("Yours faithfully,", styles["BodyReport"]), Spacer(1, 5)])
    signature = _user_signature(exporting_user)
    if signature:
        signature_image = ReportImage(
            BytesIO(signature["data"]),
            width=45 * mm,
            height=18 * mm,
            kind="proportional",
        )
        signature_image.hAlign = "LEFT"
        story.append(signature_image)
    else:
        story.append(_pdf_paragraph("Signature not uploaded", styles["BodyReport"]))
    story.extend([
        _pdf_paragraph(data["exported_by"], styles["BodyReport"]),
        _pdf_paragraph("Authorized Laboratory Officer", styles["BodyReport"]),
    ])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(20 * mm, 12 * mm, f"{data['case_code']} • Poultry Diagnostic Laboratory")
        canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(output, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title=f"Laboratory Report {data['case_code']}").build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{data["case_code"]}-report.pdf"'
    return response


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
ET.register_namespace("w", _W)
ET.register_namespace("r", _REL)
ET.register_namespace("wp", _WP)
ET.register_namespace("a", _A)
ET.register_namespace("pic", _PIC)


def _word_paragraph(parent, text, *, style=None, bold=False):
    paragraph = ET.SubElement(parent, f"{{{_W}}}p")
    properties = ET.SubElement(paragraph, f"{{{_W}}}pPr")
    if style:
        ET.SubElement(properties, f"{{{_W}}}pStyle", {f"{{{_W}}}val": style})
    run = ET.SubElement(paragraph, f"{{{_W}}}r")
    if bold:
        run_properties = ET.SubElement(run, f"{{{_W}}}rPr")
        ET.SubElement(run_properties, f"{{{_W}}}b")
    value = ET.SubElement(run, f"{{{_W}}}t", {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
    value.text = str(text or "—")
    return paragraph


def _word_table(parent, rows):
    table = ET.SubElement(parent, f"{{{_W}}}tbl")
    properties = ET.SubElement(table, f"{{{_W}}}tblPr")
    borders = ET.SubElement(properties, f"{{{_W}}}tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        ET.SubElement(borders, f"{{{_W}}}{edge}", {f"{{{_W}}}val": "single", f"{{{_W}}}sz": "4", f"{{{_W}}}color": "B9C4D0"})
    for row_values in rows:
        row = ET.SubElement(table, f"{{{_W}}}tr")
        for cell_value in row_values:
            cell = ET.SubElement(row, f"{{{_W}}}tc")
            _word_paragraph(cell, cell_value)


def _word_image(parent, image_info, relationship_id, name, width_inches=1.4, alignment="center"):
    paragraph = ET.SubElement(parent, f"{{{_W}}}p")
    properties = ET.SubElement(paragraph, f"{{{_W}}}pPr")
    ET.SubElement(properties, f"{{{_W}}}jc", {f"{{{_W}}}val": alignment})
    run = ET.SubElement(paragraph, f"{{{_W}}}r")
    drawing = ET.SubElement(run, f"{{{_W}}}drawing")
    inline = ET.SubElement(drawing, f"{{{_WP}}}inline", {
        "distT": "0", "distB": "0", "distL": "0", "distR": "0",
    })
    cx = int(width_inches * 914400)
    cy = int(cx * image_info["height"] / max(image_info["width"], 1))
    ET.SubElement(inline, f"{{{_WP}}}extent", {"cx": str(cx), "cy": str(cy)})
    ET.SubElement(inline, f"{{{_WP}}}docPr", {"id": "1" if name == "logo" else "2", "name": name})
    frame = ET.SubElement(inline, f"{{{_WP}}}cNvGraphicFramePr")
    ET.SubElement(frame, f"{{{_A}}}graphicFrameLocks", {"noChangeAspect": "1"})
    graphic = ET.SubElement(inline, f"{{{_A}}}graphic")
    graphic_data = ET.SubElement(graphic, f"{{{_A}}}graphicData", {
        "uri": _PIC,
    })
    picture = ET.SubElement(graphic_data, f"{{{_PIC}}}pic")
    non_visual = ET.SubElement(picture, f"{{{_PIC}}}nvPicPr")
    ET.SubElement(non_visual, f"{{{_PIC}}}cNvPr", {"id": "0", "name": name})
    ET.SubElement(non_visual, f"{{{_PIC}}}cNvPicPr")
    fill = ET.SubElement(picture, f"{{{_PIC}}}blipFill")
    ET.SubElement(fill, f"{{{_A}}}blip", {f"{{{_REL}}}embed": relationship_id})
    stretch = ET.SubElement(fill, f"{{{_A}}}stretch")
    ET.SubElement(stretch, f"{{{_A}}}fillRect")
    shape = ET.SubElement(picture, f"{{{_PIC}}}spPr")
    transform = ET.SubElement(shape, f"{{{_A}}}xfrm")
    ET.SubElement(transform, f"{{{_A}}}off", {"x": "0", "y": "0"})
    ET.SubElement(transform, f"{{{_A}}}ext", {"cx": str(cx), "cy": str(cy)})
    geometry = ET.SubElement(shape, f"{{{_A}}}prstGeom", {"prst": "rect"})
    ET.SubElement(geometry, f"{{{_A}}}avLst")
    return paragraph


def docx_response(sample, report=None, exporting_user=None):
    data = build_report_data(sample, report, exporting_user=exporting_user)
    document = ET.Element(f"{{{_W}}}document")
    body = ET.SubElement(document, f"{{{_W}}}body")
    image_parts = []
    logo = _lab_logo()
    if logo:
        _word_image(body, logo, "rIdLogo", "logo", width_inches=1.35)
        image_parts.append(("rIdLogo", "logo", logo))
    _word_paragraph(body, data["lab_name"], style="Title", bold=True)
    _word_paragraph(body, data["lab_address"])
    _word_paragraph(body, data["lab_email"])
    _word_table(body, [
        ["CLIENT", data["client"], "DATE", data["date"].strftime("%B %d, %Y")],
        ["CASE NO.", data["case_code"], "SAMPLE", data["sample_type"]],
    ])
    _word_paragraph(body, "Dear Sir/Ma,")
    _word_paragraph(body, f"Find below the result of {data['sample_type']} analysis carried out on the sample submitted for laboratory investigation.")

    def heading(label):
        _word_paragraph(body, label, style="Heading1", bold=True)

    if data["clinical_details"]:
        heading("Flock and Clinical History")
        for label, value in data["clinical_details"]:
            _word_paragraph(body, f"{label}: {value}")
    if data["pathology"]:
        heading("Necropsy Findings")
        _word_paragraph(body, data["pathology"])
    if data["clinical_diagnosis"]:
        heading("Clinical Diagnosis")
        _word_paragraph(body, data["clinical_diagnosis"])
    if data["laboratory_diagnosis"]:
        heading("Laboratory Diagnosis")
        _word_paragraph(body, data["laboratory_diagnosis"])
    if data["isolate"]:
        heading("Isolate")
        _word_paragraph(body, data["isolate"])
    for assay in data["assay_results"]:
        heading(assay["assay"])
        _word_paragraph(body, f"Entered by: {assay['performed_by']}")
        if assay["table"]:
            _word_table(body, [["Antimicrobial", "Interpretation"]] + [list(row) for row in assay["table"]])
        else:
            for label, value in assay["rows"]:
                _word_paragraph(body, f"{label}: {value}")
        if assay["remarks"]:
            _word_paragraph(body, f"Remarks: {assay['remarks']}")
    if data["comments"]:
        heading("Comments and Recommendations")
        _word_paragraph(body, data["comments"])
    _word_paragraph(body, "Yours faithfully,")
    signature = _user_signature(exporting_user)
    if signature:
        _word_image(body, signature, "rIdSignature", "signature", width_inches=1.7, alignment="left")
        image_parts.append(("rIdSignature", "signature", signature))
    else:
        _word_paragraph(body, "Signature not uploaded")
    _word_paragraph(body, data["exported_by"])
    _word_paragraph(body, "Authorized Laboratory Officer")
    section_properties = ET.SubElement(body, f"{{{_W}}}sectPr")
    page_size = ET.SubElement(section_properties, f"{{{_W}}}pgSz", {f"{{{_W}}}w": "11906", f"{{{_W}}}h": "16838"})
    page_size.tail = ""

    document_xml = ET.tostring(document, encoding="utf-8", xml_declaration=True)
    content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="{_CT}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    relationships = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{_PKG_REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    relationships_xml = [f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="../styles.xml"/>']
    for relationship_id, name, image_info in image_parts:
        relationships_xml.append(
            f'<Relationship Id="{relationship_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}.{image_info["extension"]}"/>'
        )
    document_relationships = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{_PKG_REL}">{''.join(relationships_xml)}</Relationships>'''
    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{_W}"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="19334D"/><w:sz w:val="30"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="19334D"/><w:sz w:val="26"/></w:rPr></w:style></w:styles>'''
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", document_relationships)
        archive.writestr("word/styles.xml", styles)
        for _relationship_id, name, image_info in image_parts:
            archive.writestr(
                f"word/media/{name}.{image_info['extension']}",
                image_info["data"],
            )
    response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    response["Content-Disposition"] = f'attachment; filename="{data["case_code"]}-report.docx"'
    return response
