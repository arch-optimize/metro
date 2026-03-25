import io
from collections import defaultdict

import plotly.io as pio
import plotly.graph_objects as go
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader


def _secs_to_hms(secs):
    try:
        s = int(secs)
        return f"{(s // 3600)%24:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    except (ValueError, TypeError):
        return str(secs)


def _draw_params_block(p, params, top_y, W, MARGIN, ACCENT):
    """Render a two-column parameters table. Returns the y coordinate of the bottom row."""
    row_h = 13
    col_w = (W - 2 * MARGIN) / 2
    items       = list(params.items())
    left_items  = items[: (len(items) + 1) // 2]
    right_items = items[(len(items) + 1) // 2 :]

    p.setFont("Helvetica-Bold", 10)
    p.setFillColorRGB(*ACCENT)
    p.drawString(MARGIN, top_y, "Parameters")
    y = top_y - 14
    p.setFillColorRGB(0, 0, 0)

    for i, (k, v) in enumerate(left_items):
        yy = y - i * row_h
        if i % 2 == 0:
            p.setFillColorRGB(0.97, 0.95, 0.96)
            p.rect(MARGIN, yy - 2, W - 2 * MARGIN, row_h, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(MARGIN + 4, yy, f"{k}:")
        p.setFont("Helvetica", 8)
        p.drawString(MARGIN + 4 + 130, yy, str(v))
    for i, (k, v) in enumerate(right_items):
        yy = y - i * row_h
        if i % 2 == 0:
            p.setFillColorRGB(0.97, 0.95, 0.96)
            p.rect(MARGIN + col_w, yy - 2, col_w, row_h, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(MARGIN + col_w + 4, yy, f"{k}:")
        p.setFont("Helvetica", 8)
        p.drawString(MARGIN + col_w + 4 + 130, yy, str(v))

    return y - max(len(left_items), len(right_items)) * row_h


def _draw_figure_on_page(p, fig_or_bytes, title_str, top_y, W, H, MARGIN, ACCENT, font_size=14):
    """Write a series title then draw a figure image, fitting it in the available space."""
    p.setFont("Helvetica-Bold", font_size)
    p.setFillColorRGB(*ACCENT)
    p.drawString(MARGIN, top_y, title_str)
    p.setFillColorRGB(0, 0, 0)

    if isinstance(fig_or_bytes, (bytes, bytearray)):
        img_bytes = fig_or_bytes
    else:
        img_bytes = pio.to_image(fig_or_bytes, format="png", engine="kaleido", width=900)

    reader = ImageReader(io.BytesIO(img_bytes))
    iw, ih = reader.getSize()
    avail_w = W - 2 * MARGIN
    avail_h = top_y - 20 - 40  # space below title, above bottom margin
    scale   = min(avail_w / iw, avail_h / ih)
    dw, dh  = iw * scale, ih * scale
    p.drawImage(reader, MARGIN, top_y - 20 - dh, width=dw, height=dh)
    return top_y - 20 - dh  # bottom y of image


def generate_pdf_report(fig_dict, table_data=None, title="Metro Analytics Report", params=None):
    if isinstance(fig_dict, go.Figure):
        fig = fig_dict
    else:
        fig = go.Figure(
            data=fig_dict.get("data", []),
            layout=fig_dict.get("layout", {}),
        )

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    ACCENT = (0.54, 0.08, 0.31)
    MARGIN = 50

    # ── Detect multi-subplot figure (fw/lw/mv/vp have one trace per yaxis) ────
    unique_yaxes = sorted(
        {getattr(t, 'yaxis', None) or 'y' for t in fig.data},
        key=lambda x: int(x[1:]) if x[1:].isdigit() else 0,
    )
    is_multi = len(unique_yaxes) > 1

    if is_multi:
        # ── Cover page: title + parameters ──────────────────────────────────
        p.setFont("Helvetica-Bold", 18)
        p.setFillColorRGB(*ACCENT)
        p.drawString(MARGIN, H - 50, title)
        p.setFillColorRGB(0, 0, 0)

        if params:
            _draw_params_block(p, params, H - 80, W, MARGIN, ACCENT)
        else:
            p.setFont("Helvetica", 11)
            p.drawString(MARGIN, H - 90, "Individual series follow on the next pages.")

        # ── One page per series ──────────────────────────────────────────────
        annots = list(fig.layout.annotations) if fig.layout.annotations else []
        for j, ya in enumerate(unique_yaxes):
            p.showPage()
            series_label = annots[j].text if j < len(annots) else f"Series {j + 1}"

            # Rebuild a clean single-subplot figure from this series' traces
            sub_traces = [
                go.Scatter(x=list(t.x), y=list(t.y), mode=getattr(t, 'mode', 'lines') or 'lines')
                for t in fig.data
                if (getattr(t, 'yaxis', None) or 'y') == ya
            ]
            sub_fig = go.Figure(data=sub_traces)
            sub_fig.update_layout(
                template="plotly_white",
                height=480,
                xaxis_title="Time of day",
                margin={"t": 40, "b": 60, "l": 60, "r": 30},
            )
            _draw_figure_on_page(p, sub_fig, series_label, H - 50, W, H, MARGIN, ACCENT)

        p.save()
        return buffer.getvalue()

    # ── Single-subplot path (unchanged behaviour) ─────────────────────────────
    img_bytes = pio.to_image(fig, format="png", engine="kaleido", width=900)

    # ── Page 1: title + graph ─────────────────────────────────────────────────
    p.setFont("Helvetica-Bold", 18)
    p.setFillColorRGB(*ACCENT)
    p.drawString(MARGIN, H - 50, title)
    p.setFillColorRGB(0, 0, 0)

    img_reader = ImageReader(io.BytesIO(img_bytes))
    img_w, img_h = img_reader.getSize()
    avail_w  = W - 2 * MARGIN
    avail_h  = H - 80
    scale    = min(avail_w / img_w, avail_h / img_h)
    draw_w   = img_w * scale
    draw_h   = img_h * scale
    img_bottom = H - 70 - draw_h
    p.drawImage(img_reader, MARGIN, img_bottom, width=draw_w, height=draw_h)

    # ── Parameters block: below graph if space remains, else new page ─────────
    if params:
        params_top = img_bottom - 18
        row_h     = 13
        n_rows    = (len(params) + 1) // 2
        needed    = 16 + n_rows * row_h

        if params_top - needed < 40:
            p.showPage()
            params_top = H - 50

        _draw_params_block(p, params, params_top, W, MARGIN, ACCENT)

    if not table_data:
        p.save()
        return buffer.getvalue()

    # ── Group departures by loop ───────────────────────────────────────────────
    fwd = defaultdict(list)
    bwd = defaultdict(list)
    loop_order = []
    for row in table_data:
        direction = row.get("direction", "")
        dep = row.get("departure", "")
        time_str = _secs_to_hms(dep + 4 * 3600)
        if "Forward" in direction:
            key = direction.replace("Forward ", "").strip()
            if key not in loop_order:
                loop_order.append(key)
            fwd[key].append(time_str)
        elif "Backward" in direction:
            key = direction.replace("Backward ", "").strip()
            if key not in loop_order:
                loop_order.append(key)
            bwd[key].append(time_str)

    # ── Timetable pages ────────────────────────────────────────────────────────
    MARGIN_L  = 50
    MARGIN_R  = 50
    COL_W     = (W - MARGIN_L - MARGIN_R) / 2
    ROW_H     = 14
    HDR_H     = 18
    ACCENT    = (0.54, 0.08, 0.31)   # #8a1550
    LIGHT     = (0.93, 0.87, 0.90)   # #eedde5

    def new_timetable_page():
        p.showPage()
        y = H - 40
        p.setFont("Helvetica-Bold", 13)
        p.setFillColorRGB(*ACCENT)
        p.drawString(MARGIN_L, y, f"{title} — Timetable (continued)")
        p.setFillColorRGB(0, 0, 0)
        return y - 24

    p.showPage()
    y = H - 40
    p.setFont("Helvetica-Bold", 14)
    p.setFillColorRGB(*ACCENT)
    p.drawString(MARGIN_L, y, f"{title} — Full Timetable")
    p.setFillColorRGB(0, 0, 0)
    y -= 24

    for loop in loop_order:
        f_rows = fwd.get(loop, [])
        b_rows = bwd.get(loop, [])
        max_rows = max(len(f_rows), len(b_rows))

        # Space needed: loop header + col header + rows
        needed = HDR_H + ROW_H + max_rows * ROW_H + 12
        if y - needed < 40:
            y = new_timetable_page()

        # Loop sub-header
        p.setFont("Helvetica-Bold", 11)
        p.setFillColorRGB(*ACCENT)
        p.drawString(MARGIN_L, y, f"Loop: {loop}")
        p.setFillColorRGB(0, 0, 0)
        y -= HDR_H

        # Column headers
        p.setFont("Helvetica-Bold", 9)
        p.setFillColorRGB(0.3, 0.3, 0.3)
        p.drawString(MARGIN_L + 4, y, "Forward (HH:MM:SS)")
        p.drawString(MARGIN_L + COL_W + 4, y, "Backward (HH:MM:SS)")
        p.setFillColorRGB(0, 0, 0)
        y -= ROW_H - 2

        # Separator line
        p.setStrokeColorRGB(*LIGHT)
        p.setLineWidth(0.5)
        p.line(MARGIN_L, y + 4, W - MARGIN_R, y + 4)
        y -= 4

        # Data rows
        p.setFont("Helvetica", 9)
        for i in range(max_rows):
            if y < 40:
                y = new_timetable_page()
                p.setFont("Helvetica", 9)

            # Alternating row shading
            if i % 2 == 0:
                p.setFillColorRGB(0.98, 0.96, 0.97)
                p.rect(MARGIN_L, y - 2, W - MARGIN_L - MARGIN_R, ROW_H, fill=1, stroke=0)
            p.setFillColorRGB(0, 0, 0)

            f_val = f_rows[i] if i < len(f_rows) else "—"
            b_val = b_rows[i] if i < len(b_rows) else "—"
            p.drawString(MARGIN_L + 4, y, f_val)
            p.drawString(MARGIN_L + COL_W + 4, y, b_val)
            y -= ROW_H

        y -= 14  # gap between loops

    p.save()
    return buffer.getvalue()


def generate_graph_image(fig_dict, format="png"):
    fig = go.Figure(fig_dict)
    return pio.to_image(fig, format=format, engine="kaleido")


def generate_metrics_pdf_report(figures, title="Processing Quality Metrics"):
    """Render a list of Plotly figures (dicts or go.Figure) into a single PDF, one per page."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    ACCENT = (0.54, 0.08, 0.31)

    for i, fig_dict in enumerate(figures):
        if i > 0:
            p.showPage()

        fig = fig_dict if isinstance(fig_dict, go.Figure) else go.Figure(
            data=fig_dict.get("data", []),
            layout=fig_dict.get("layout", {}),
        )

        try:
            fig_title = (fig.layout.title.text or "").strip() or title
        except Exception:
            fig_title = title

        header = title if i == 0 else fig_title
        p.setFont("Helvetica-Bold", 16 if i == 0 else 13)
        p.setFillColorRGB(*ACCENT)
        p.drawString(40, H - 50, header)
        if i == 0 and fig_title != title:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(40, H - 70, fig_title)
        p.setFillColorRGB(0, 0, 0)

        img_bytes = pio.to_image(fig, format="png", engine="kaleido", width=1100, height=500)
        img_reader = ImageReader(io.BytesIO(img_bytes))
        p.drawImage(img_reader, 30, H - 530, width=W - 60, preserveAspectRatio=True)

    p.save()
    return buffer.getvalue()
