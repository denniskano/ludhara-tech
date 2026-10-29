#!/usr/bin/env python3
"""Genera calculadora-temporal-cloud.xlsx (fórmulas nativas, celdas amarillas = input)."""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.properties import CalcProperties

N_WF = 20
N_STEPS = 150

TIPOS = [
    ("Activity", 1),
    ("Local Activities (1 por WFT)", 1),
    ("Timer / timeout SDK", 1),
    ("Signal", 1),
    ("Signal externo", 1),
    ("Query", 1),
    ("Update", 1),
    ("Child (hijo NO listado)", 2),
    ("Continue-As-New", 1),
    ("Upsert Search Attributes", 1),
    ("Nexus Operation (caller)", 1),
    ("WFT Heartbeat (LA largas)", 1),
]

ORIGENES = ["Cliente", "Signal-With-Start", "Schedule", "Ninguno"]

SAMPLE_WF = [
    ("Pago interbancario", 50000, "Cliente", 0.4, 80, 30),
    ("Alta de cliente", 8000, "Schedule", 2.5, 120, 30),
]

SAMPLE_STEPS = [
    ("Pago interbancario", "Activity", "Validar cuenta", 1, 100, 0, 0),
    ("Pago interbancario", "Activity", "Débito core", 1, 98, 0.3, 4),
    ("Pago interbancario", "Activity", "Crédito destino", 1, 95, 0.4, 6),
    ("Pago interbancario", "Activity", "Notificar", 1, 100, 0, 0),
    ("Pago interbancario", "Timer / timeout SDK", "Espera SLA / AwaitWithTimeout", 1, 15, 0, 0),
    ("Pago interbancario", "Signal", "Confirmación manual", 1, 8, 0, 0),
    ("Pago interbancario", "Query", "Consulta estado UI", 2, 40, 0, 0),
    ("Alta de cliente", "Activity", "KYC", 1, 100, 1, 12),
    ("Alta de cliente", "Activity", "Crear producto", 1, 85, 0.2, 2),
    ("Alta de cliente", "Timer / timeout SDK", "Espera documentos", 1, 30, 0, 0),
    ("Alta de cliente", "Signal", "Documentos listos", 1, 30, 0, 0),
    ("Alta de cliente", "Child (hijo NO listado)", "Onboarding cards (no listado)", 1, 60, 0, 0),
]


def styles():
    thin = Border(
        left=Side(style="thin", color="D0D5DD"),
        right=Side(style="thin", color="D0D5DD"),
        top=Side(style="thin", color="D0D5DD"),
        bottom=Side(style="thin", color="D0D5DD"),
    )
    return {
        "title": Font(name="Calibri", size=16, bold=True, color="FFFFFF"),
        "h": Font(name="Calibri", size=10, bold=True, color="FFFFFF"),
        "cell": Font(name="Calibri", size=10, color="1D2939"),
        "mono": Font(name="Consolas", size=9, color="1D2939"),
        "thin": thin,
        "fill_title": PatternFill("solid", fgColor="1B4F72"),
        "fill_h": PatternFill("solid", fgColor="154360"),
        "fill_in": PatternFill("solid", fgColor="FFF3C4"),
        "fill_out": PatternFill("solid", fgColor="E8F6F3"),
        "fill_alt": PatternFill("solid", fgColor="F8FAFC"),
        "wrap": Alignment(wrap_text=True, vertical="center"),
        "right": Alignment(horizontal="right", vertical="center"),
    }


def header_row(ws, headers, s):
    for col, h in enumerate(headers, 1):
        c = ws.cell(1, col, h)
        c.font = s["h"]
        c.fill = s["fill_h"]
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        c.border = s["thin"]
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"


def widths(ws, wsizes):
    for i, w in enumerate(wsizes, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def paint(cell, s, fill, num=None):
    cell.font = s["cell"]
    cell.fill = fill
    cell.border = s["thin"]
    cell.alignment = s["wrap"]
    if num:
        cell.number_format = num


def sheet_tarifas(wb, s):
    ws = wb.active
    ws.title = "Tarifas"
    ws.sheet_properties.tabColor = "1B4F72"
    ws.merge_cells("A1:C1")
    t = ws["A1"]
    t.value = "Temporal Cloud — tarifas commitment 3 años (celdas amarillas = input)"
    t.font = s["title"]
    t.fill = s["fill_title"]
    ws.row_dimensions[1].height = 28

    ws["A3"] = "Parámetro"
    ws["B3"] = "Valor"
    ws["C3"] = "Nota"
    for col in range(1, 4):
        ws.cell(3, col).font = s["h"]
        ws.cell(3, col).fill = s["fill_h"]
        ws.cell(3, col).border = s["thin"]

    rows = [
        (4, "RATE_ACTIONS", "Actions ($ / millón)", 23.16, "Contrato. List público empieza en $50/millón."),
        (5, "RATE_ACTIVE", "Active Storage ($ / GB-h)", 0.039, "Contrato. List público $0.042/GBh."),
        (6, "RATE_RETAINED", "Retained Storage ($ / GB-h)", 0.00105, "Igual al list público."),
        (7, "HORAS_MES", "Horas / mes (referencia GB)", 730, "Temporal usa 744 h para GB incluidos del plan. No entra en Actions."),
    ]
    for r, name, label, val, note in rows:
        ws.cell(r, 1, label)
        paint(ws.cell(r, 1), s, s["fill_alt"])
        c = ws.cell(r, 2, val)
        paint(c, s, s["fill_in"], "#,##0.00000")
        ws.cell(r, 3, note)
        paint(ws.cell(r, 3), s, s["fill_alt"])
        wb.defined_names.add(DefinedName(name, attr_text=f"Tarifas!$B${r}"))

    ws["A9"] = "Cómo leer"
    ws["A9"].font = Font(name="Calibri", size=12, bold=True, color="1B4F72")
    notes = [
        "1. Hoja Workflows: un type por fila (nombre, ejecuciones/mes, origen, duración open, KB de history, retention).",
        "2. Hoja Pasos: detail de cada type. Veces × (% camino/100) × unidad oficial. Activity suma retries y heartbeats.",
        "3. Hoja Resumen: totales del mes. Amarillo = input. Verde = fórmula. No editar verde.",
        "4. Origen Cliente = 1 start_workflow. Signal-With-Start = 1. Schedule = 3 (incluye el start). Ninguno = 0.",
        "5. Child (hijo NO listado) = 2 Actions. Si el hijo es otra fila en Workflows, no uses ese tipo en el padre.",
        "6. Storage activo = exec × (KB/1024/1024) × horas open. Retenido = exec × GB × días × 24. Régimen mensual, no invoice.",
        "7. Replay no factura. Heartbeat solo si llega al server (SDK ~80% del Heartbeat Timeout).",
        "8. Fuentes: https://docs.temporal.io/cloud/actions  y  https://docs.temporal.io/cloud/pricing",
    ]
    for i, line in enumerate(notes):
        ws.cell(10 + i, 1, line).alignment = s["wrap"]
        ws.merge_cells(start_row=10 + i, start_column=1, end_row=10 + i, end_column=3)
        ws.row_dimensions[10 + i].height = 20

    widths(ws, [42, 16, 78])
    ws.freeze_panes = "A4"
    return ws


def sheet_listas(wb, s):
    ws = wb.create_sheet("Listas")
    ws.sheet_properties.tabColor = "6941C6"
    ws["A1"] = "Origen"
    ws["B1"] = "Tipo de paso"
    ws["C1"] = "Actions unitarias"
    for col in range(1, 4):
        ws.cell(1, col).font = s["h"]
        ws.cell(1, col).fill = s["fill_h"]
        ws.cell(1, col).border = s["thin"]
    for i, o in enumerate(ORIGENES, 2):
        ws.cell(i, 1, o)
        paint(ws.cell(i, 1), s, s["fill_alt"])
    for i, (t, u) in enumerate(TIPOS, 2):
        ws.cell(i, 2, t)
        ws.cell(i, 3, u)
        paint(ws.cell(i, 2), s, s["fill_alt"])
        paint(ws.cell(i, 3), s, s["fill_alt"], "0")
    wb.defined_names.add(DefinedName("ORIGENES", attr_text="Listas!$A$2:$A$5"))
    wb.defined_names.add(DefinedName("TIPOS", attr_text="Listas!$B$2:$B$13"))
    wb.defined_names.add(DefinedName("TIPO_UNIDAD", attr_text="Listas!$B$2:$C$13"))
    widths(ws, [22, 36, 18])
    return ws


def sheet_workflows(wb, s):
    ws = wb.create_sheet("Workflows")
    ws.sheet_properties.tabColor = "027A48"
    headers = [
        "Nombre (type)",
        "Ejecuciones / mes",
        "Origen",
        "Actions origen",
        "Duración open (h)",
        "History promedio (KB)",
        "Retention (días)",
        "Actions/exec (pasos)",
        "Actions / mes",
        "Active GBh",
        "Retained GBh",
        "USD Actions",
        "USD Active",
        "USD Retained",
        "USD total",
    ]
    header_row(ws, headers, s)
    last = N_WF + 1
    for r in range(2, last + 1):
        i = r - 2
        sample = SAMPLE_WF[i] if i < len(SAMPLE_WF) else None
        name = sample[0] if sample else ""
        exec_n = sample[1] if sample else ""
        origin = sample[2] if sample else "Cliente"
        dur = sample[3] if sample else ""
        kb = sample[4] if sample else ""
        ret = sample[5] if sample else 30

        paint(ws.cell(r, 1, name), s, s["fill_in"])
        c = ws.cell(r, 2, exec_n if exec_n != "" else None)
        paint(c, s, s["fill_in"], "#,##0")
        paint(ws.cell(r, 3, origin if sample else ""), s, s["fill_in"])
        d = ws.cell(r, 4, f'=IF(A{r}="","",IF(C{r}="Cliente",1,IF(C{r}="Signal-With-Start",1,IF(C{r}="Schedule",3,0))))')
        paint(d, s, s["fill_out"], "0")
        e = ws.cell(r, 5, dur if dur != "" else None)
        paint(e, s, s["fill_in"], "0.00")
        f = ws.cell(r, 6, kb if kb != "" else None)
        paint(f, s, s["fill_in"], "#,##0")
        g = ws.cell(r, 7, ret if sample else None)
        paint(g, s, s["fill_in"], "0")
        h = ws.cell(
            r,
            8,
            f'=IF(A{r}="","",SUMIF(Pasos!$A$2:$A${N_STEPS+1},A{r},Pasos!$I$2:$I${N_STEPS+1}))',
        )
        paint(h, s, s["fill_out"], "0.00")
        ii = ws.cell(r, 9, f'=IF(A{r}="","",B{r}*(D{r}+H{r}))')
        paint(ii, s, s["fill_out"], "#,##0.00")
        j = ws.cell(r, 10, f'=IF(A{r}="","",B{r}*(F{r}/1024/1024)*E{r})')
        paint(j, s, s["fill_out"], "#,##0.000")
        k = ws.cell(r, 11, f'=IF(A{r}="","",B{r}*(F{r}/1024/1024)*G{r}*24)')
        paint(k, s, s["fill_out"], "#,##0.000")
        l = ws.cell(r, 12, f'=IF(A{r}="","",I{r}/1000000*RATE_ACTIONS)')
        paint(l, s, s["fill_out"], '"$"#,##0.00')
        m = ws.cell(r, 13, f'=IF(A{r}="","",J{r}*RATE_ACTIVE)')
        paint(m, s, s["fill_out"], '"$"#,##0.00')
        nn = ws.cell(r, 14, f'=IF(A{r}="","",K{r}*RATE_RETAINED)')
        paint(nn, s, s["fill_out"], '"$"#,##0.00')
        o = ws.cell(r, 15, f'=IF(A{r}="","",L{r}+M{r}+N{r})')
        paint(o, s, s["fill_out"], '"$"#,##0.00')
        ws.row_dimensions[r].height = 20

    wb.defined_names.add(DefinedName("WF_NAMES", attr_text=f"Workflows!$A$2:$A${last}"))
    dv = DataValidation(type="list", formula1="=Listas!$A$2:$A$5", allow_blank=True)
    dv.error = "Elige Cliente, Signal-With-Start, Schedule o Ninguno"
    dv.errorTitle = "Origen"
    dv.showErrorMessage = True
    dv.showDropDown = False
    ws.add_data_validation(dv)
    dv.add(f"C2:C{last}")
    ws.auto_filter.ref = f"A1:O{last}"
    widths(ws, [28, 18, 22, 14, 16, 20, 16, 18, 16, 14, 14, 14, 14, 14, 14])
    return ws


def sheet_pasos(wb, s):
    ws = wb.create_sheet("Pasos")
    ws.sheet_properties.tabColor = "FDB022"
    headers = [
        "Workflow (type)",
        "Tipo de paso",
        "Nombre del paso",
        "Veces si el camino ocurre",
        "% del flujo",
        "Retries avg (solo Activity)",
        "Heartbeats avg (solo Activity)",
        "Unidad oficial",
        "Actions / ejecución",
    ]
    header_row(ws, headers, s)
    last = N_STEPS + 1
    for r in range(2, last + 1):
        i = r - 2
        sample = SAMPLE_STEPS[i] if i < len(SAMPLE_STEPS) else None
        if sample:
            ws.cell(r, 1, sample[0])
            ws.cell(r, 2, sample[1])
            ws.cell(r, 3, sample[2])
            ws.cell(r, 4, sample[3])
            ws.cell(r, 5, sample[4])
            ws.cell(r, 6, sample[5])
            ws.cell(r, 7, sample[6])
        else:
            for col in range(1, 8):
                ws.cell(r, col, None)
        for col in range(1, 8):
            paint(ws.cell(r, col), s, s["fill_in"])
        ws.cell(r, 4).number_format = "0.00"
        ws.cell(r, 5).number_format = "0"
        ws.cell(r, 6).number_format = "0.00"
        ws.cell(r, 7).number_format = "0.00"
        h = ws.cell(
            r,
            8,
            f'=IF(B{r}="","",IFERROR(VLOOKUP(B{r},Listas!$B$2:$C$13,2,0),1))',
        )
        paint(h, s, s["fill_out"], "0")
        # Activity: veces * pct/100 * (1 + retries + heartbeats)
        ii = ws.cell(
            r,
            9,
            f'=IF(OR(A{r}="",B{r}=""),"",IF(B{r}="Activity",D{r}*(E{r}/100)*(1+N(F{r})+N(G{r})),D{r}*(E{r}/100)*H{r}))',
        )
        paint(ii, s, s["fill_out"], "0.000")
        ws.row_dimensions[r].height = 18

    dv_wf = DataValidation(type="list", formula1=f"=Workflows!$A$2:$A${N_WF+1}", allow_blank=True)
    dv_wf.error = "Elige un nombre de la hoja Workflows"
    dv_wf.errorTitle = "Workflow"
    dv_wf.showErrorMessage = True
    dv_wf.showDropDown = False
    ws.add_data_validation(dv_wf)
    dv_wf.add(f"A2:A{last}")
    dv_t = DataValidation(type="list", formula1="=Listas!$B$2:$B$13", allow_blank=True)
    dv_t.error = "Elige un tipo de la hoja Listas"
    dv_t.errorTitle = "Tipo"
    dv_t.showErrorMessage = True
    dv_t.showDropDown = False
    ws.add_data_validation(dv_t)
    dv_t.add(f"B2:B{last}")
    ws.auto_filter.ref = f"A1:I{last}"
    widths(ws, [26, 32, 36, 22, 14, 24, 26, 16, 18])
    return ws


def sheet_resumen(wb, s):
    ws = wb.create_sheet("Resumen", 1)  # after Tarifas; Workflows already exists
    ws.sheet_properties.tabColor = "B42318"
    ws.merge_cells("A1:D1")
    t = ws["A1"]
    t.value = "Resumen mensual — Temporal Cloud (commitment 3 años)"
    t.font = s["title"]
    t.fill = s["fill_title"]
    ws.row_dimensions[1].height = 28

    ws["A3"] = "Indicador"
    ws["B3"] = "Cantidad"
    ws["C3"] = "USD / mes"
    for col in range(1, 4):
        ws.cell(3, col).font = s["h"]
        ws.cell(3, col).fill = s["fill_h"]
        ws.cell(3, col).border = s["thin"]

    last_wf = N_WF + 1
    lines = [
        (4, "Tipos de workflow con nombre", f'=COUNTA(Workflows!A2:A{last_wf})', None),
        (5, "Ejecuciones / mes", f"=SUMIF(Workflows!A2:A{last_wf},\"<>\",Workflows!B2:B{last_wf})", None),
        (6, "Actions / mes", f"=SUMIF(Workflows!A2:A{last_wf},\"<>\",Workflows!I2:I{last_wf})", f"=B6/1000000*RATE_ACTIONS"),
        (7, "Actions (millones)", f"=B6/1000000", None),
        (8, "Actions / ejecución (media)", f'=IF(B5=0,0,B6/B5)', None),
        (9, "Active Storage (GBh)", f"=SUMIF(Workflows!A2:A{last_wf},\"<>\",Workflows!J2:J{last_wf})", f"=B9*RATE_ACTIVE"),
        (10, "Retained Storage (GBh)", f"=SUMIF(Workflows!A2:A{last_wf},\"<>\",Workflows!K2:K{last_wf})", f"=B10*RATE_RETAINED"),
        (11, "GB activo equivalente (GBh / horas mes)", f"=IF(HORAS_MES=0,0,B9/HORAS_MES)", None),
        (12, "TOTAL USD / mes", f"=N(C6)+N(C9)+N(C10)", f"=B12"),
    ]
    for r, label, qty, usd in lines:
        ws.cell(r, 1, label)
        paint(ws.cell(r, 1), s, s["fill_alt"])
        paint(ws.cell(r, 2, qty), s, s["fill_out"], "#,##0.000")
        if usd:
            paint(ws.cell(r, 3, usd), s, s["fill_out"], '"$"#,##0.00')
        else:
            paint(ws.cell(r, 3, "-"), s, s["fill_alt"])

    ws["B5"].number_format = "#,##0"
    ws["B6"].number_format = "#,##0.00"
    ws["B4"].number_format = "0"
    ws["C12"].fill = PatternFill("solid", fgColor="AAF0C4")
    ws["A12"].fill = PatternFill("solid", fgColor="AAF0C4")
    ws["B12"].fill = PatternFill("solid", fgColor="AAF0C4")
    ws["A12"].font = Font(name="Calibri", size=11, bold=True)
    ws["B12"].font = Font(name="Calibri", size=11, bold=True)
    ws["C12"].font = Font(name="Calibri", size=11, bold=True)

    ws["A14"] = "Costo por workflow type: columnas L-O de la hoja Workflows."
    ws["A14"].font = Font(name="Calibri", size=12, bold=True, color="1B4F72")
    ws.merge_cells("A14:D14")

    ws["A16"] = (
        "Estimado de regimen, no la factura. Temporal documenta hasta 5% de diferencia entre metricas OpenMetrics y metering. "
        "No incluye Support, Export, Fairness ni TRU ociosos. Abrir en Excel para Windows o Microsoft 365: Habilitar edicion si aparece Vista protegida."
    )
    ws["A16"].alignment = s["wrap"]
    ws.merge_cells("A16:D16")
    ws.row_dimensions[16].height = 40
    widths(ws, [48, 18, 16, 16])
    return ws


def sheet_catalogo(wb, s):
    ws = wb.create_sheet("Catalogo")
    ws.sheet_properties.tabColor = "155EEF"
    ws.merge_cells("A1:D1")
    t = ws["A1"]
    t.value = "Catálogo oficial de Actions (referencia, no input)"
    t.font = s["title"]
    t.fill = s["fill_title"]
    headers = ["En la calculadora", "Usage / metric name", "Actions", "Nota oficial"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(3, col, h)
        c.font = s["h"]
        c.fill = s["fill_h"]
        c.border = s["thin"]
    rows = [
        ("Origen Cliente", "start_workflow", "1", "Start vía client. Dedup por Workflow ID no cuenta."),
        ("Origen Signal-With-Start", "signal_workflow_with_start", "1", "Un Action total, arranque o no."),
        ("Origen Schedule", "schedule start + start_workflow", "3", "Schedule Start cuenta 2; el workflow 1."),
        ("Activity", "schedule_activity + retry_activity + record_activity_heartbeat", "1 + retries + HB", "HB solo si llega al server. SDK throttle ~80% del timeout."),
        ("Local Activities (1 por WFT)", "record_activity_markers", "1 por Workflow Task", "N Local Activities del mismo WFT = 1 Action."),
        ("Timer / timeout SDK", "start_timer", "1", "Incluye AwaitWithTimeout / condition."),
        ("Signal", "signal_workflow", "1", "Client o workflow."),
        ("Signal externo", "signal_external_workflow", "1", "En el history del signaled."),
        ("Query", "query_workflow", "1", "Incluye call stack en UI Cloud. __temporal_workflow_metadata excluida."),
        ("Update", "accept_workflow_update / reject_workflow_update", "1", "Dedup por Update ID no cuenta."),
        ("Child (hijo NO listado)", "start_child_workflow + start", "2", "Intent + intento de start. Si el hijo es otra fila, no uses este tipo."),
        ("Continue-As-New", "continue_as_new_workflow", "1", "El nuevo run también tiene su start."),
        ("Upsert Search Attributes", "upsert_workflow_search_attributes", "1 por comando", "Varios SA en un comando = 1. SA al start no cuentan."),
        ("Nexus Operation (caller)", "schedule_nexus_operation", "1 en caller", "El handler factura sus primitives aparte."),
        ("WFT Heartbeat (LA largas)", "record_workflow_heartbeat", "1", "Local Activities largas que latean el WFT."),
        ("Replay", "-", "0", "No factura. Solo worker."),
    ]
    for i, row in enumerate(rows):
        r = 4 + i
        for col, val in enumerate(row, 1):
            ws.cell(r, col, val)
            paint(ws.cell(r, col), s, s["fill_alt"])
        ws.row_dimensions[r].height = 32
    ws["A21"] = "https://docs.temporal.io/cloud/actions"
    ws["A21"].hyperlink = "https://docs.temporal.io/cloud/actions"
    ws["A21"].font = Font(name="Calibri", size=10, color="155EEF", underline="single")
    ws["A22"] = "https://docs.temporal.io/cloud/pricing"
    ws["A22"].hyperlink = "https://docs.temporal.io/cloud/pricing"
    ws["A22"].font = Font(name="Calibri", size=10, color="155EEF", underline="single")
    widths(ws, [36, 52, 28, 72])
    return ws


def main():
    wb = Workbook()
    wb.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True, calcId=191029)
    wb.properties.creator = "ludhara-tech"
    wb.properties.title = "Calculadora Temporal Cloud"
    s = styles()
    sheet_tarifas(wb, s)
    sheet_listas(wb, s)
    sheet_workflows(wb, s)
    sheet_pasos(wb, s)
    sheet_resumen(wb, s)
    sheet_catalogo(wb, s)

    # defined name clash check
    banned = {"RF", "C", "R"}
    for n in list(wb.defined_names.keys()):
        if n in banned:
            raise SystemExit(f"defined name forbidden: {n}")

    out = Path(__file__).resolve().parent / "calculadora-temporal-cloud.xlsx"
    wb.save(out)
    print(f"wrote {out}: {N_WF} workflow slots, {N_STEPS} step rows")


if __name__ == "__main__":
    main()
