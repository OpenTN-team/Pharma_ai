"""
pdf_export.py — Export PDF pour PharmAssist
Génère deux types de documents :
  1. Planning hebdomadaire (tableau imprimable)
  2. Rapport de conformité RH complet
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus import PageBreak

from data import EMPLOYES, PHARMACIE
from store import load_store
from Rulesengine import run_full_compliance_check

# ─────────────────────────────────────────────
# PALETTE DE COULEURS (cohérente avec l'UI)
# ─────────────────────────────────────────────
C_DARK       = colors.HexColor("#0d1f3c")
C_BLUE       = colors.HexColor("#2563eb")
C_BLUE_LIGHT = colors.HexColor("#63b3ed")
C_GREEN      = colors.HexColor("#16a34a")
C_GREEN_LIGHT= colors.HexColor("#68d391")
C_ORANGE     = colors.HexColor("#d97706")
C_RED        = colors.HexColor("#dc2626")
C_GRAY       = colors.HexColor("#64748b")
C_GRAY_LIGHT = colors.HexColor("#f1f5f9")
C_WHITE      = colors.white
C_BLACK      = colors.HexColor("#1e293b")

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
JOURS_LABELS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]


# ═════════════════════════════════════════════
#  STYLES COMMUNS
# ═════════════════════════════════════════════

def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="PharmTitle",
        fontSize=22, fontName="Helvetica-Bold",
        textColor=C_DARK, alignment=TA_LEFT,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="PharmSubtitle",
        fontSize=11, fontName="Helvetica",
        textColor=C_GRAY, alignment=TA_LEFT,
        spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="PharmBadge",
        fontSize=9, fontName="Helvetica-Bold",
        textColor=C_BLUE, alignment=TA_LEFT,
        spaceAfter=16
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontSize=13, fontName="Helvetica-Bold",
        textColor=C_DARK, spaceBefore=16, spaceAfter=8,
        borderPad=4
    ))
    styles.add(ParagraphStyle(
        name="SmallGray",
        fontSize=8, fontName="Helvetica",
        textColor=C_GRAY, alignment=TA_LEFT
    ))
    styles.add(ParagraphStyle(
        name="SmallGrayCenter",
        fontSize=8, fontName="Helvetica",
        textColor=C_GRAY, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name="ViolationRed",
        fontSize=9, fontName="Helvetica",
        textColor=C_RED, spaceAfter=4, leftIndent=8
    ))
    styles.add(ParagraphStyle(
        name="ViolationOrange",
        fontSize=9, fontName="Helvetica",
        textColor=C_ORANGE, spaceAfter=4, leftIndent=8
    ))
    styles.add(ParagraphStyle(
        name="ConformeGreen",
        fontSize=9, fontName="Helvetica",
        textColor=C_GREEN, spaceAfter=3, leftIndent=8
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        fontSize=10, fontName="Helvetica",
        textColor=C_BLACK, spaceAfter=6
    ))
    return styles


def _header_block(styles, titre: str, sous_titre: str) -> list:
    """Bloc d'en-tête commun aux deux types de documents."""
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    return [
        Paragraph("PHARMASSIST — AGENT RH INTELLIGENT", styles["PharmBadge"]),
        Paragraph(titre, styles["PharmTitle"]),
        Paragraph(f"{PHARMACIE['nom']} · {PHARMACIE['ville']}", styles["PharmSubtitle"]),
        Paragraph(sous_titre, styles["PharmSubtitle"]),
        Paragraph(f"Généré le {now}", styles["SmallGray"]),
        HRFlowable(width="100%", thickness=2, color=C_BLUE, spaceAfter=16),
    ]


# ═════════════════════════════════════════════
#  EXPORT 1 — PLANNING HEBDOMADAIRE
# ═════════════════════════════════════════════

def export_planning_pdf() -> bytes:
    """
    Génère le planning de la semaine en cours sous forme de PDF.
    Retourne les bytes du PDF (pour st.download_button).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm
    )
    styles = _get_styles()
    store = load_store()
    planning = store["planning"]
    pde_noms = {e["nom"] for e in EMPLOYES if e["qualifie"]}
    story = []

    # En-tête
    story += _header_block(styles, "Planning Hebdomadaire", "Semaine en cours — Convention Collective IDCC 1996")

    # ── Tableau principal planning ──
    story.append(Paragraph("Planning par employé", styles["SectionTitle"]))

    # En-têtes colonnes
    header_row = [Paragraph("<b>Employé</b>", styles["SmallGrayCenter"]),
                  Paragraph("<b>Rôle</b>", styles["SmallGrayCenter"])]
    for label in JOURS_LABELS:
        header_row.append(Paragraph(f"<b>{label}</b>", styles["SmallGrayCenter"]))

    table_data = [header_row]

    for emp in EMPLOYES:
        nom = emp["nom"]
        role_label = "PDE" if emp["qualifie"] else "Prépar."
        row = [
            Paragraph(nom, styles["SmallGray"]),
            Paragraph(role_label, styles["SmallGrayCenter"]),
        ]
        for jour in JOURS:
            matin = nom in planning.get(jour, {}).get("matin", [])
            am    = nom in planning.get(jour, {}).get("apres_midi", [])
            if matin and am:
                cell = Paragraph("Journée", styles["SmallGrayCenter"])
            elif matin:
                cell = Paragraph("Matin", styles["SmallGrayCenter"])
            elif am:
                cell = Paragraph("Ap-midi", styles["SmallGrayCenter"])
            else:
                cell = Paragraph("—", styles["SmallGrayCenter"])
            row.append(cell)
        table_data.append(row)

    col_widths = [42*mm, 18*mm] + [22*mm] * 6
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 6),
        # Body
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("ALIGN",        (2, 1), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GRAY_LIGHT]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROUNDEDCORNERS", [3]),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # ── Tableau effectif par jour ──
    story.append(Paragraph("Effectif par créneau", styles["SectionTitle"]))

    eff_header = [
        Paragraph("<b>Jour</b>", styles["SmallGrayCenter"]),
        Paragraph("<b>Matin</b>", styles["SmallGrayCenter"]),
        Paragraph("<b>PDE matin</b>", styles["SmallGrayCenter"]),
        Paragraph("<b>Après-midi</b>", styles["SmallGrayCenter"]),
        Paragraph("<b>PDE ap-midi</b>", styles["SmallGrayCenter"]),
    ]
    eff_data = [eff_header]

    for jour, label in zip(JOURS, JOURS_LABELS):
        matin_eq  = planning.get(jour, {}).get("matin", [])
        am_eq     = planning.get(jour, {}).get("apres_midi", [])
        pde_matin = [e for e in matin_eq if e in pde_noms]
        pde_am    = [e for e in am_eq    if e in pde_noms]

        pde_m_style = styles["ConformeGreen"] if pde_matin else styles["ViolationRed"]
        pde_a_style = styles["ConformeGreen"] if pde_am    else styles["ViolationRed"]

        eff_data.append([
            Paragraph(label, styles["SmallGray"]),
            Paragraph(str(len(matin_eq)), styles["SmallGrayCenter"]),
            Paragraph(", ".join(pde_matin) or "AUCUN !", pde_m_style),
            Paragraph(str(len(am_eq)), styles["SmallGrayCenter"]),
            Paragraph(", ".join(pde_am)  or "AUCUN !", pde_a_style),
        ])

    eff_widths = [28*mm, 20*mm, 50*mm, 20*mm, 50*mm]
    t2 = Table(eff_data, colWidths=eff_widths, repeatRows=1)
    t2.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), C_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 6),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GRAY_LIGHT]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t2)

    # ── Légende ──
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Convention Collective Pharmacie IDCC 1996 — Un PDE doit être présent à chaque créneau d'ouverture.",
        styles["SmallGray"]
    ))

    doc.build(story)
    return buffer.getvalue()


# ═════════════════════════════════════════════
#  EXPORT 2 — RAPPORT DE CONFORMITÉ
# ═════════════════════════════════════════════

def export_conformite_pdf() -> bytes:
    """
    Génère le rapport de conformité IDCC 1996 complet en PDF.
    Retourne les bytes du PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm
    )
    styles = _get_styles()
    rapport = run_full_compliance_check()
    r = rapport["rapport"]
    story = []

    # En-tête
    story += _header_block(
        styles,
        "Rapport de Conformite RH",
        f"Analyse complete — Score: {r['score_conformite']}%"
    )

    # ── Score global ──
    score = r["score_conformite"]
    score_color = C_GREEN if score >= 90 else C_ORANGE if score >= 75 else C_RED
    score_label = "CONFORME" if score >= 90 else "ATTENTION" if score >= 75 else "NON CONFORME"

    score_data = [[
        Paragraph(f"<b>{score}%</b>", ParagraphStyle(
            "ScoreNum", fontSize=28, fontName="Helvetica-Bold",
            textColor=score_color, alignment=TA_CENTER
        )),
        Paragraph(f"<b>{score_label}</b>", ParagraphStyle(
            "ScoreLabel", fontSize=14, fontName="Helvetica-Bold",
            textColor=score_color, alignment=TA_LEFT, spaceBefore=8
        )),
        Paragraph(
            f"<b>{r['total_verifications']}</b> verifications<br/>"
            f"<font color='#16a34a'>{r['conformes']} conformes</font><br/>"
            f"<font color='#dc2626'>{r['violations_critiques']} critiques</font><br/>"
            f"<font color='#d97706'>{r['violations_mineures']} mineures</font>",
            ParagraphStyle("ScoreSub", fontSize=10, fontName="Helvetica",
                           textColor=C_BLACK, alignment=TA_LEFT, leading=16)
        ),
    ]]

    score_table = Table(score_data, colWidths=[35*mm, 60*mm, 70*mm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), C_GRAY_LIGHT),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",       (0, 0), (0, 0),   "CENTER"),
        ("TOPPADDING",  (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING",(0,0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("BOX",         (0, 0), (-1, -1), 2, score_color),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 16))

    # ── Violations critiques ──
    if rapport["violations_critiques"]:
        story.append(KeepTogether([
            Paragraph("Violations Critiques", styles["SectionTitle"]),
        ]))
        viol_data = [
            [Paragraph("<b>Code</b>", styles["SmallGrayCenter"]),
             Paragraph("<b>Description</b>", styles["SmallGrayCenter"]),
             Paragraph("<b>Détails</b>", styles["SmallGrayCenter"])]
        ]
        for v in rapport["violations_critiques"]:
            details = ", ".join(f"{k}: {val}" for k, val in v.get("details", {}).items())
            viol_data.append([
                Paragraph(v["code"], ParagraphStyle("CodeRed", fontSize=8,
                    fontName="Helvetica-Bold", textColor=C_RED)),
                Paragraph(v["message"], styles["SmallGray"]),
                Paragraph(details[:120], styles["SmallGray"]),
            ])
        vt = Table(viol_data, colWidths=[38*mm, 90*mm, 42*mm], repeatRows=1)
        vt.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_RED),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1),
             [colors.HexColor("#fff5f5"), C_WHITE]),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(vt)
        story.append(Spacer(1, 12))
    else:
        story.append(Paragraph(
            "Aucune violation critique detectee.", styles["ConformeGreen"]
        ))

    # ── Violations mineures ──
    if rapport["violations_mineures"]:
        story.append(Paragraph("Violations Mineures", styles["SectionTitle"]))
        for v in rapport["violations_mineures"]:
            story.append(Paragraph(f"• [{v['code']}] {v['message']}", styles["ViolationOrange"]))
        story.append(Spacer(1, 10))

    # ── Points conformes (résumé groupé) ──
    story.append(Paragraph("Points Conformes", styles["SectionTitle"]))
    conformes_uniques: dict[str, int] = {}
    for v in rapport["points_conformes"]:
        conformes_uniques[v["code"]] = conformes_uniques.get(v["code"], 0) + 1

    conf_data = [[
        Paragraph("<b>Code</b>", styles["SmallGrayCenter"]),
        Paragraph("<b>Occurrences</b>", styles["SmallGrayCenter"]),
        Paragraph("<b>Statut</b>", styles["SmallGrayCenter"]),
    ]]
    for code, count in conformes_uniques.items():
        conf_data.append([
            Paragraph(code, ParagraphStyle("CodeGreen", fontSize=8,
                fontName="Helvetica-Bold", textColor=C_GREEN)),
            Paragraph(str(count), styles["SmallGrayCenter"]),
            Paragraph("Conforme", ParagraphStyle("OK", fontSize=8,
                fontName="Helvetica-Bold", textColor=C_GREEN, alignment=TA_CENTER)),
        ])

    ct = Table(conf_data, colWidths=[55*mm, 35*mm, 80*mm], repeatRows=1)
    ct.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_GREEN),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),
         [colors.HexColor("#f0fdf4"), C_WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    story.append(ct)

    # ── Absences ──
    story.append(PageBreak())
    story.append(Paragraph("Absences Enregistrees", styles["SectionTitle"]))
    store = load_store()
    absences = store.get("absences", [])

    if absences:
        abs_data = [[
            Paragraph("<b>Employe</b>",    styles["SmallGrayCenter"]),
            Paragraph("<b>Date</b>",       styles["SmallGrayCenter"]),
            Paragraph("<b>Type</b>",       styles["SmallGrayCenter"]),
            Paragraph("<b>Statut</b>",     styles["SmallGrayCenter"]),
            Paragraph("<b>Remplacant</b>", styles["SmallGrayCenter"]),
        ]]
        for a in absences:
            statut_color = C_GREEN if a["statut"] == "Validée" else \
                           C_RED if a["statut"] == "Refusée" else C_ORANGE
            abs_data.append([
                Paragraph(a["employe"], styles["SmallGray"]),
                Paragraph(a["date"], styles["SmallGrayCenter"]),
                Paragraph(a["type"], styles["SmallGray"]),
                Paragraph(a["statut"], ParagraphStyle(
                    "StatutStyle", fontSize=8, fontName="Helvetica-Bold",
                    textColor=statut_color, alignment=TA_CENTER
                )),
                Paragraph(a.get("remplacant") or "—", styles["SmallGrayCenter"]),
            ])
        at = Table(abs_data, colWidths=[45*mm, 28*mm, 32*mm, 28*mm, 37*mm], repeatRows=1)
        at.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GRAY_LIGHT]),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(at)
    else:
        story.append(Paragraph("Aucune absence enregistree.", styles["SmallGray"]))

    # ── Pied de page légal ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=C_GRAY, spaceAfter=8))
    story.append(Paragraph(
        "Document genere automatiquement par PharmAssist · "
        "Convention Collective Nationale de la Pharmacie d'officine (IDCC 1996) · "
        "A conserver dans le dossier RH",
        styles["SmallGray"]
    ))

    doc.build(story)
    return buffer.getvalue()
