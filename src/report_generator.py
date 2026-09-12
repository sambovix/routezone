"""Excel report generator for supply chain network optimization results."""

import io
from typing import Dict, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.network_analyzer import BaselineComparison, CurrencyConvertedBreakdown
from src.optimizer import OptimizationResult


def generate_excel_report(
    result: OptimizationResult,
    currency_breakdown: CurrencyConvertedBreakdown,
    baseline_comparison: Optional[BaselineComparison] = None,
) -> io.BytesIO:
    """Compile multi-tab executive workbook with network decisions and financials.

    Args:
        result: OptimizationResult from solver.
        currency_breakdown: Converted financial breakdown.
        baseline_comparison: Optional baseline comparison metrics.

    Returns:
        BytesIO buffer containing valid XLSX workbook.
    """
    wb = openpyxl.Workbook()

    # Styling specifications
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    section_font = Font(name="Calibri", size=13, bold=True, color="1F4E78")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    sym = currency_breakdown.symbol
    curr = currency_breakdown.currency
    factor = 1.0 / currency_breakdown.exchange_rate

    # Sheet 1: Executive Summary
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    ws_summary.views.sheetView[0].showGridLines = True

    ws_summary["A1"] = "SUPPLY CHAIN NETWORK OPTIMIZATION: EXECUTIVE SUMMARY"
    ws_summary["A1"].font = section_font
    ws_summary.row_dimensions[1].height = 25

    summary_kpis = [
        ("Solver Optimization Status", result.solver_status),
        ("Reporting Currency", f"{curr} ({sym})"),
        ("FX Conversion Rate (DZD per unit)", currency_breakdown.exchange_rate),
        ("Total Network Demand (units/month)", f"{result.kpis.total_demand:,.0f}"),
        ("Active Distribution Centers", result.kpis.open_facility_count),
        ("Weighted Average Lead Time (days)", f"{result.kpis.weighted_average_lead_time_days:.2f}"),
        ("Total Landed Cost", f"{sym} {currency_breakdown.total_landed_cost:,.2f}"),
        ("Landed Cost per Unit", f"{sym} {currency_breakdown.cost_per_unit:,.4f}"),
    ]

    if baseline_comparison:
        summary_kpis.extend([
            ("Status Quo Baseline Cost", f"{sym} {baseline_comparison.baseline_total_cost:,.2f}"),
            ("Annualized Net Savings", f"{sym} {baseline_comparison.absolute_savings:,.2f}"),
            ("Relative Cost Reduction", f"{baseline_comparison.percentage_savings:.1f}%"),
            ("Transit Time Reduction", f"{baseline_comparison.lead_time_reduction_days:.1f} day(s)"),
        ])

    row_idx = 3
    for label, val in summary_kpis:
        ws_summary.cell(row=row_idx, column=1, value=label).font = bold_font
        ws_summary.cell(row=row_idx, column=2, value=val).font = regular_font
        ws_summary.cell(row=row_idx, column=1).border = thin_border
        ws_summary.cell(row=row_idx, column=2).border = thin_border
        row_idx += 1

    # Sheet 2: Facility Decisions
    ws_fac = wb.create_sheet(title="Distribution Centers")
    ws_fac.views.sheetView[0].showGridLines = True
    fac_headers = [
        "Facility ID",
        "Facility Name",
        "Status",
        "Assigned Volume (units)",
        "Max Capacity (units)",
        "Utilization Rate (%)",
        f"Fixed Cost ({curr})",
        f"Handling Cost ({curr})",
    ]
    for col_idx, h in enumerate(fac_headers, start=1):
        cell = ws_fac.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for f_idx, f in enumerate(result.facilities, start=2):
        ws_fac.cell(row=f_idx, column=1, value=f.facility_id)
        ws_fac.cell(row=f_idx, column=2, value=f.facility_name)
        ws_fac.cell(row=f_idx, column=3, value="OPEN" if f.is_open else "CLOSED")
        ws_fac.cell(row=f_idx, column=4, value=f.assigned_throughput)
        ws_fac.cell(row=f_idx, column=5, value=f.max_capacity)
        ws_fac.cell(row=f_idx, column=6, value=f.utilization_rate * 100.0)
        ws_fac.cell(row=f_idx, column=7, value=round(f.fixed_cost * factor, 2))
        ws_fac.cell(row=f_idx, column=8, value=round(f.variable_cost * factor, 2))
        for c in range(1, 9):
            ws_fac.cell(row=f_idx, column=c).border = thin_border

    # Sheet 3: Regional Assignments
    ws_assign = wb.create_sheet(title="Customer Allocation")
    ws_assign.views.sheetView[0].showGridLines = True
    assign_headers = [
        "Region ID",
        "Region Name",
        "Serving DC ID",
        "Serving DC Name",
        "Demand Served (units)",
        "Transit Lead Time (days)",
        f"Unit Outbound Cost ({curr})",
        f"Total Outbound Freight ({curr})",
    ]
    for col_idx, h in enumerate(assign_headers, start=1):
        cell = ws_assign.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for a_idx, a in enumerate(result.assignments, start=2):
        ws_assign.cell(row=a_idx, column=1, value=a.region_id)
        ws_assign.cell(row=a_idx, column=2, value=a.region_name)
        ws_assign.cell(row=a_idx, column=3, value=a.serving_facility_id)
        ws_assign.cell(row=a_idx, column=4, value=a.serving_facility_name)
        ws_assign.cell(row=a_idx, column=5, value=a.demand_served)
        ws_assign.cell(row=a_idx, column=6, value=a.lead_time_days)
        ws_assign.cell(row=a_idx, column=7, value=round(a.outbound_unit_cost * factor, 4))
        ws_assign.cell(row=a_idx, column=8, value=round(a.outbound_total_cost * factor, 2))
        for c in range(1, 9):
            ws_assign.cell(row=a_idx, column=c).border = thin_border

    # Sheet 4: Upstream Replenishment Flows
    ws_inflow = wb.create_sheet(title="Inbound Supply Flows")
    ws_inflow.views.sheetView[0].showGridLines = True
    inflow_headers = [
        "Supplier ID",
        "Supplier Name",
        "Destination DC ID",
        "Destination DC Name",
        "Replenishment Volume (units)",
        f"Unit Inbound Freight ({curr})",
        f"Total Inbound Freight ({curr})",
    ]
    for col_idx, h in enumerate(inflow_headers, start=1):
        cell = ws_inflow.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for i_idx, fl in enumerate(result.inbound_flows, start=2):
        ws_inflow.cell(row=i_idx, column=1, value=fl.supplier_id)
        ws_inflow.cell(row=i_idx, column=2, value=fl.supplier_name)
        ws_inflow.cell(row=i_idx, column=3, value=fl.facility_id)
        ws_inflow.cell(row=i_idx, column=4, value=fl.facility_name)
        ws_inflow.cell(row=i_idx, column=5, value=fl.volume_units)
        ws_inflow.cell(row=i_idx, column=6, value=round(fl.unit_cost * factor, 4))
        ws_inflow.cell(row=i_idx, column=7, value=round(fl.total_cost * factor, 2))
        for c in range(1, 8):
            ws_inflow.cell(row=i_idx, column=c).border = thin_border

    # Sheet 5: Financial Decomposition
    ws_fin = wb.create_sheet(title="Landed Cost Breakdown")
    ws_fin.views.sheetView[0].showGridLines = True
    fin_headers = [
        "Cost Category",
        f"Amount ({curr})",
        "Amount (Base DZD)",
        "Share of Total (%)",
    ]
    for col_idx, h in enumerate(fin_headers, start=1):
        cell = ws_fin.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    tot_amt = currency_breakdown.total_landed_cost
    tot_dzd = result.cost_breakdown.total_landed_cost

    cost_rows = [
        (
            "Fixed Facility Overhead",
            currency_breakdown.fixed_facility_cost,
            result.cost_breakdown.fixed_facility_cost,
        ),
        (
            "Variable Handling Expenditure",
            currency_breakdown.variable_handling_cost,
            result.cost_breakdown.variable_handling_cost,
        ),
        (
            "Inbound Primary Freight",
            currency_breakdown.inbound_freight_cost,
            result.cost_breakdown.inbound_freight_cost,
        ),
        (
            "Outbound Secondary Freight",
            currency_breakdown.outbound_freight_cost,
            result.cost_breakdown.outbound_freight_cost,
        ),
        (
            "TOTAL LANDED COST",
            currency_breakdown.total_landed_cost,
            result.cost_breakdown.total_landed_cost,
        ),
    ]

    for r_idx, (cat, amt, dzd) in enumerate(cost_rows, start=2):
        share = (amt / tot_amt * 100.0) if tot_amt > 0 else 0.0
        ws_fin.cell(row=r_idx, column=1, value=cat).font = (
            bold_font if "TOTAL" in cat else regular_font
        )
        ws_fin.cell(row=r_idx, column=2, value=amt).font = (
            bold_font if "TOTAL" in cat else regular_font
        )
        ws_fin.cell(row=r_idx, column=3, value=dzd).font = (
            bold_font if "TOTAL" in cat else regular_font
        )
        ws_fin.cell(row=r_idx, column=4, value=round(share, 1)).font = (
            bold_font if "TOTAL" in cat else regular_font
        )
        for c in range(1, 5):
            ws_fin.cell(row=r_idx, column=c).border = thin_border

    # Auto-fit column widths across all sheets
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
