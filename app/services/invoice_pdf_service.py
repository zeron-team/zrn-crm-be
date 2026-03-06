"""
Invoice PDF Generator for Argentine Fiscal Invoices
Generates PDFs with 3 copies: ORIGINAL, DUPLICADO, TRIPLICADO
Includes AFIP/ARCA QR code as per RG 4291/2018

Professional layout compliant with RG 1415 format.
"""
import os
import io
import json
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fpdf import FPDF
import qrcode

logger = logging.getLogger(__name__)

# --- Constants ---
PAGE_W = 210
PAGE_H = 297
MARGIN = 8
CONTENT_W = PAGE_W - 2 * MARGIN
MID_X = PAGE_W / 2


class InvoicePDF(FPDF):
    """Custom FPDF class for Argentine fiscal invoices"""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)


# --- Text helpers ---

def _sanitize_text(text: str) -> str:
    """Replace Unicode chars not supported by built-in Helvetica"""
    if not text:
        return ""
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00b0": "o",
        "\u2022": "*", "\u00ba": "o", "\u00aa": "a", "\u2039": "<",
        "\u203a": ">", "\u2010": "-", "\u2011": "-", "\u2012": "-",
        "\u00e9": "e", "\u00e1": "a", "\u00ed": "i", "\u00f3": "o",
        "\u00fa": "u", "\u00f1": "n", "\u00c9": "E", "\u00c1": "A",
        "\u00cd": "I", "\u00d3": "O", "\u00da": "U", "\u00d1": "N",
        "\u00fc": "u",
    }
    for uchar, replacement in replacements.items():
        text = text.replace(uchar, replacement)
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text


def _format_cuit(cuit: str) -> str:
    cuit = str(cuit).replace("-", "").strip()
    if len(cuit) == 11:
        return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
    return cuit


def _format_currency(amount: float) -> str:
    if amount is None:
        amount = 0
    formatted = f"{abs(amount):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if amount < 0 else ""
    return f"{sign}${formatted}"


def _format_date(date_str: str) -> str:
    if not date_str:
        return ""
    s = str(date_str).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[6:8]}/{s[4:6]}/{s[:4]}"
    if "-" in s:
        parts = s[:10].split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return s


def _get_cbte_letter(cbte_tipo: int) -> str:
    mapping = {1: "A", 2: "A", 3: "A", 6: "B", 7: "B", 8: "B",
               11: "C", 12: "C", 13: "C", 19: "E", 51: "M"}
    return mapping.get(cbte_tipo, "C")


def _get_cbte_name(cbte_tipo: int) -> str:
    mapping = {
        1: "FACTURA", 2: "NOTA DE DEBITO", 3: "NOTA DE CREDITO",
        6: "FACTURA", 7: "NOTA DE DEBITO", 8: "NOTA DE CREDITO",
        11: "FACTURA", 12: "NOTA DE DEBITO", 13: "NOTA DE CREDITO",
        19: "FACTURA DE EXPORTACION", 51: "FACTURA",
    }
    return mapping.get(cbte_tipo, "FACTURA")


def _get_iva_condition_label(cond: int) -> str:
    mapping = {
        1: "IVA Responsable Inscripto",
        4: "IVA Sujeto Exento",
        5: "Consumidor Final",
        6: "Responsable Monotributo",
        7: "Sujeto No Categorizado",
        8: "Proveedor del Exterior",
        9: "Cliente del Exterior",
        10: "IVA Liberado",
        11: "IVA Resp. Inscripto - Ag. Percepcion",
    }
    return mapping.get(cond, "Consumidor Final")


def _concepto_label(c: int) -> str:
    return {1: "Productos", 2: "Servicios", 3: "Productos y Servicios"}.get(c, "Productos")


# --- QR Code ---

def generate_afip_qr(data: Dict) -> Optional[str]:
    try:
        qr_data = {
            "ver": 1,
            "fecha": _format_date(data.get("fecha_cbte", "")).replace("/", "-")
                     if "/" in _format_date(data.get("fecha_cbte", ""))
                     else data.get("fecha_cbte", ""),
            "cuit": int(str(data.get("emitter_cuit", "0")).replace("-", "")),
            "ptoVta": data.get("punto_vta", 0),
            "tipoCmp": data.get("cbte_tipo", 11),
            "nroCmp": data.get("cbte_nro", 0),
            "importe": round(float(data.get("imp_total", 0)), 2),
            "moneda": data.get("mon_id", "PES"),
            "ctz": round(float(data.get("mon_cotiz", 1)), 2),
            "tipoDocRec": data.get("tipo_doc", 80),
            "nroDocRec": int(str(data.get("nro_doc", "0")).replace("-", "")),
            "tipoCodAut": "E",
            "codAut": int(data.get("cae", "0") or "0"),
        }
        json_str = json.dumps(qr_data)
        b64 = base64.b64encode(json_str.encode()).decode()
        url = f"https://www.afip.gob.ar/fe/qr/?p={b64}"

        qr = qrcode.QRCode(version=1, box_size=3, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        tmp_path = f"/tmp/qr_inv_{data.get('cbte_nro', 0)}_{os.getpid()}.png"
        img.save(tmp_path)
        return tmp_path
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        return None


# --- Main page drawing ---

def _draw_invoice_page(pdf: InvoicePDF, data: Dict, copy_label: str):
    """Draw a single invoice page matching standard Argentine fiscal invoice layout."""
    pdf.add_page()

    S = _sanitize_text  # shorthand

    letter = _get_cbte_letter(data.get("cbte_tipo", 11))
    cbte_name = _get_cbte_name(data.get("cbte_tipo", 11))
    punto_vta = data.get("punto_vta", 4)
    cbte_nro = data.get("cbte_nro", 0)
    cbte_tipo = data.get("cbte_tipo", 11)
    is_credit_note = cbte_tipo in (3, 8, 13)
    concepto = data.get("concepto", 1)

    # Page border
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.4)
    pdf.rect(MARGIN, MARGIN, CONTENT_W, PAGE_H - 2 * MARGIN)

    # --- COPY LABEL ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(MARGIN, MARGIN + 2)
    pdf.cell(CONTENT_W, 6, copy_label, align="C")

    # --- LETTER BADGE (top center) ---
    badge_w = 16
    badge_h = 20
    badge_x = MID_X - badge_w / 2
    badge_y = MARGIN + 10
    pdf.set_line_width(0.5)
    pdf.rect(badge_x, badge_y, badge_w, badge_h)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_xy(badge_x, badge_y + 1)
    pdf.cell(badge_w, 13, letter, align="C")
    pdf.set_font("Helvetica", "", 6)
    pdf.set_xy(badge_x, badge_y + 14)
    pdf.cell(badge_w, 5, S(f"COD. {str(cbte_tipo).zfill(3)}"), align="C")

    # --- RIGHT OF BADGE: Invoice type + number ---
    rx = badge_x + badge_w + 4
    rw = MARGIN + CONTENT_W - rx - 2

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(rx, badge_y)
    pdf.cell(rw, 7, S(cbte_name), align="L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(rx, badge_y + 9)
    pdf.cell(48, 4, S(f"Punto de Venta: {str(punto_vta).zfill(5)}"))
    pdf.cell(45, 4, S(f"Comp. Nro: {str(cbte_nro).zfill(8)}"))

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(rx, badge_y + 15)
    pdf.cell(rw, 4, S(f"Fecha de Emision:  {_format_date(data.get('fecha_cbte', ''))}"))

    # --- EMITTER SECTION (below badge) ---
    ey = badge_y + badge_h + 3
    ex = MARGIN + 2

    # Razon Social (full width, bold)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(ex, ey)
    pdf.cell(40, 4, "Razon Social:")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(55, 4, S(data.get("emitter_razon_social", "").upper())[:45])

    # Right side: CUIT
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(MID_X + 5, ey)
    pdf.cell(15, 4, "CUIT:")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(40, 4, _format_cuit(data.get("emitter_cuit", "")))
    ey += 5

    # Domicilio + Ing. Brutos
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(ex, ey)
    pdf.cell(30, 4, "Domicilio Comercial:")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(65, 4, S(data.get("emitter_domicilio", ""))[:50])

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(MID_X + 5, ey)
    pdf.cell(25, 4, "Ingresos Brutos:")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(40, 4, data.get("emitter_cuit", "").replace("-", ""))
    ey += 5

    # Condicion IVA + Inicio Actividades
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(ex, ey)
    pdf.cell(35, 4, "Condicion frente al IVA:")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(55, 4, S(_get_iva_condition_label(data.get("emitter_condicion_iva", 6))))

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(MID_X + 5, ey)
    pdf.cell(38, 4, "Fecha de Inicio de Actividades:")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(30, 4, _format_date(data.get("emitter_inicio_act", "")))
    ey += 6

    # --- Separator ---
    pdf.set_line_width(0.3)
    pdf.line(MARGIN, ey, MARGIN + CONTENT_W, ey)

    # --- SERVICE PERIOD + VTO PAGO ---
    py = ey + 1
    if concepto in (2, 3):
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(ex, py)
        desde = _format_date(data.get("fecha_serv_desde", ""))
        hasta = _format_date(data.get("fecha_serv_hasta", ""))
        pdf.cell(30, 4, S("Periodo Facturado Desde:"))
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(22, 4, desde)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(12, 4, "Hasta:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(22, 4, hasta)

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(MARGIN + CONTENT_W - 80, py)
    pdf.cell(40, 4, S("Fecha de Vto. para el pago:"))
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(35, 4, _format_date(data.get("fecha_venc_pago", "")))
    py += 6
    pdf.line(MARGIN, py, MARGIN + CONTENT_W, py)

    # --- RECEPTOR SECTION ---
    ry = py + 1

    nro_doc_raw = data.get("nro_doc", "")
    tipo_doc = data.get("tipo_doc", 80)
    nro_doc_fmt = _format_cuit(str(nro_doc_raw)) if tipo_doc == 80 else str(nro_doc_raw)
    doc_label = "CUIT:" if tipo_doc == 80 else "DNI:" if tipo_doc == 96 else "Doc:"

    # Row 1: Doc + Razon Social
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(ex, ry)
    pdf.cell(10, 4, S(doc_label))
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(28, 4, S(nro_doc_fmt))

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(MID_X - 20, ry)
    pdf.cell(48, 4, "Apellido y Nombre / Razon Social:", align="R")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(60, 4, S(data.get("client_name", ""))[:40])
    ry += 5

    # Row 2: Cond. IVA + Domicilio
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(ex, ry)
    pdf.cell(35, 4, S("Condicion frente al IVA:"))
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(50, 4, S(_get_iva_condition_label(data.get("condicion_iva_receptor", 5))))

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(MID_X + 10, ry)
    pdf.cell(18, 4, "Domicilio:")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(60, 4, S(data.get("client_address", ""))[:45])
    ry += 5

    # Row 3: Cond. Venta + Associated invoice (for NC)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(ex, ry)
    pdf.cell(25, 4, S("Condicion de venta:"))
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(40, 4, S(data.get("condicion_venta", "Contado")))

    cbte_asoc = data.get("cbte_asoc", {})
    if is_credit_note and cbte_asoc:
        asoc_pto = cbte_asoc.get("pto_vta", 0)
        asoc_nro = cbte_asoc.get("nro", 0)
        asoc_tipo = cbte_asoc.get("tipo", 0)
        asoc_letter = _get_cbte_letter(asoc_tipo)
        asoc_str = S(f"Fac. {asoc_letter}: {str(asoc_pto).zfill(5)}-{str(asoc_nro).zfill(8)}")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(MID_X + 10, ry)
        pdf.cell(70, 4, asoc_str, align="R")

    ry += 6
    pdf.line(MARGIN, ry, MARGIN + CONTENT_W, ry)

    # --- LINE ITEMS TABLE ---
    table_y = ry + 1
    items = data.get("line_items", [])

    cols = [
        ("Codigo", 16, "C"),
        ("Producto / Servicio", 62, "L"),
        ("Cantidad", 18, "C"),
        ("U. Medida", 20, "C"),
        ("Precio Unit.", 24, "R"),
        ("% Bonif", 16, "R"),
        ("Imp. Bonif.", 18, "R"),
        ("Subtotal", 20, "R"),
    ]

    # Header
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Helvetica", "B", 6.5)
    x = MARGIN
    for header, w, _ in cols:
        pdf.set_xy(x, table_y)
        pdf.cell(w, 6, S(header), border=1, fill=True, align="C")
        x += w

    # Data rows
    y_item = table_y + 6
    pdf.set_font("Helvetica", "", 6.5)
    aligns = ["C", "L", "C", "C", "R", "R", "R", "R"]

    for idx, item in enumerate(items):
        desc = S(str(item.get("descripcion", "")))[:50]
        qty = float(item.get("cantidad", 1))
        row = [
            str(item.get("codigo", "")),
            desc,
            f"{qty:.2f}".replace(".", ","),
            str(item.get("unidad", "unidades")),
            _format_currency(item.get("precio_unitario", 0)),
            "0,00",
            "0,00",
            _format_currency(item.get("total", 0)),
        ]
        x = MARGIN
        for i, (_, w, _) in enumerate(cols):
            pdf.set_xy(x, y_item)
            pdf.cell(w, 5, row[i], border=1, align=aligns[i])
            x += w
        y_item += 5

        # Long description
        full_desc = S(str(item.get("descripcion", "")))
        if len(full_desc) > 50:
            x = MARGIN + cols[0][1]
            pdf.set_xy(x, y_item)
            pdf.cell(cols[1][1], 5, full_desc[50:100], border=1, align="L")
            y_item += 5

    # Empty fill rows
    min_y = 210
    while y_item < min_y:
        x = MARGIN
        for _, w, _ in cols:
            pdf.set_xy(x, y_item)
            pdf.cell(w, 5, "", border=1)
            x += w
        y_item += 5

    # --- TOTALS ---
    y_totals = y_item + 1

    imp_neto = float(data.get("imp_neto", 0) or 0)
    imp_iva = float(data.get("imp_iva", 0) or 0)
    imp_total = float(data.get("imp_total", 0) or 0)
    imp_tot_conc = float(data.get("imp_tot_conc", 0) or 0)
    imp_op_ex = float(data.get("imp_op_ex", 0) or 0)
    imp_trib = float(data.get("imp_trib", 0) or 0)

    tx = MARGIN + CONTENT_W - 70
    yt = y_totals

    total_rows = [("Subtotal:", imp_neto)]
    if data.get("emitter_condicion_iva", 6) != 6 and imp_iva > 0:
        total_rows.append(("IVA 21%:", imp_iva))
    total_rows.extend([
        ("Importe No Gravado:", imp_tot_conc),
        ("Importe Exento:", imp_op_ex),
        ("Otros Tributos:", imp_trib),
    ])

    for label, amount in total_rows:
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(tx, yt)
        pdf.cell(38, 4, S(label), align="R")
        pdf.cell(28, 4, _format_currency(amount), align="R")
        yt += 4.5

    pdf.set_line_width(0.3)
    pdf.line(tx, yt, tx + 66, yt)
    yt += 1
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(tx, yt)
    pdf.cell(38, 6, "IMPORTE TOTAL:", align="R")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(28, 6, _format_currency(imp_total), align="R")

    # --- CAE + QR ---
    cae = data.get("cae", "")
    cae_vto = data.get("cae_vto", "")

    y_cae = yt + 10
    pdf.set_line_width(0.3)
    pdf.line(MARGIN, y_cae, MARGIN + CONTENT_W, y_cae)

    if cae:
        qr_path = generate_afip_qr(data)
        if qr_path and os.path.exists(qr_path):
            pdf.image(qr_path, MARGIN + 3, y_cae + 2, 22, 22)
            try:
                os.remove(qr_path)
            except:
                pass

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(MARGIN + 28, y_cae + 4)
        pdf.cell(60, 4, "Comprobante Autorizado")

        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(MARGIN + 28, y_cae + 10)
        pdf.cell(14, 4, S("CAE N:"))
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(55, 4, str(cae))

        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(MARGIN + 28, y_cae + 16)
        pdf.cell(28, 4, S("Fecha de Vto. de CAE:"))
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(40, 4, _format_date(str(cae_vto)))

        pdf.set_font("Helvetica", "I", 5)
        pdf.set_text_color(120, 120, 120)
        pdf.set_xy(MARGIN + CONTENT_W - 80, y_cae + 18)
        pdf.cell(78, 3, S("Esta Admin. Federal no se responsabiliza por los datos"), align="R")
        pdf.set_xy(MARGIN + CONTENT_W - 80, y_cae + 21)
        pdf.cell(78, 3, S("ingresados en el detalle de la operacion."), align="R")
        pdf.set_text_color(0, 0, 0)

    # Page number
    pdf.set_font("Helvetica", "", 5.5)
    pdf.set_text_color(130, 130, 130)
    pdf.set_xy(MARGIN + CONTENT_W - 30, PAGE_H - MARGIN - 2)
    pdf.cell(28, 3, S("Pag. 1/1"), align="R")
    pdf.set_text_color(0, 0, 0)


# --- Public API ---

def generate_invoice_pdf(invoice_data: Dict) -> bytes:
    pdf = InvoicePDF()
    for copy_label in ["ORIGINAL", "DUPLICADO", "TRIPLICADO"]:
        _draw_invoice_page(pdf, invoice_data, copy_label)
    return pdf.output()


def generate_invoice_pdf_file(invoice_data: Dict, output_path: str) -> str:
    pdf_bytes = generate_invoice_pdf(invoice_data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    logger.info(f"Invoice PDF saved: {output_path}")
    return output_path
