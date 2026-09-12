"""Supply Chain Network Optimizer (SCNO) Two-Step Application."""

import io
from typing import Dict, Optional
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from config import DEFAULT_CURRENCY_CONFIG, DEFAULT_OPERATIONAL_CONFIG
from src.data_loader import (
    FacilitySchema,
    RegionSchema,
    SupplierSchema,
    load_facilities,
    load_regions,
    load_suppliers,
    synthesize_transport_matrices,
)
from src.network_analyzer import (
    compare_with_baseline,
    compute_baseline_status_quo,
    convert_costs_to_currency,
)
from src.optimizer import solve_facility_location
from src.carbon_engine import calculate_transport_emissions
from src.inventory_engine import calculate_safety_stock_holding
from src.greenfield_engine import compute_weiszfeld_centroid
from src.resilience_engine import simulate_single_node_disruption
from src.report_generator import generate_excel_report
from src.visualization import (
    create_network_map,
    plot_cost_breakdown_pie,
    plot_facility_utilization,
    plot_scenario_comparison,
)

st.set_page_config(
    page_title="SCNO: Supply Chain Network Optimizer",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #1f4e78;
        margin-bottom: 0.1rem;
    }
    .main-subtitle {
        font-size: 1.0rem;
        color: #555555;
        margin-bottom: 1.2rem;
    }
    .step-pill-active {
        display: inline-block;
        background-color: #1f4e78;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .step-pill-inactive {
        display: inline-block;
        background-color: #e9ecef;
        color: #495057;
        padding: 6px 14px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        padding: 12px 16px;
        text-align: left;
    }
    .metric-val {
        font-size: 1.35rem;
        font-weight: 700;
        color: #1f4e78;
    }
    .metric-lbl {
        font-size: 0.8rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .pipeline-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #f8f9fa;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 20px;
        gap: 8px;
    }
    .pipeline-step {
        flex: 1;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 10px 12px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
    .pipeline-step.active {
        border-color: #1f4e78;
        background: #f0f7ff;
        box-shadow: 0 2px 4px rgba(31, 78, 120, 0.12);
    }
    .pipeline-step .step-tag {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #1f4e78;
        background: #e1effe;
        padding: 2px 6px;
        border-radius: 4px;
        margin-bottom: 4px;
    }
    .pipeline-step .step-title {
        font-size: 0.86rem;
        font-weight: 600;
        color: #1e293b;
    }
    .pipeline-step .step-desc {
        font-size: 0.74rem;
        color: #64748b;
        margin-top: 2px;
    }
    .pipeline-arrow {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .guide-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #1f4e78;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 16px;
    }
    .guide-title {
        font-size: 0.90rem;
        font-weight: 700;
        color: #1f4e78;
        margin-bottom: 4px;
    }
    .guide-text {
        font-size: 0.82rem;
        color: #334155;
        line-height: 1.45;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_empty_datasets():
    reg = pd.DataFrame(
        columns=["region_id", "region_name", "latitude", "longitude", "demand_units_month"]
    ).astype({
        "region_id": str,
        "region_name": str,
        "latitude": float,
        "longitude": float,
        "demand_units_month": float,
    })
    sup = pd.DataFrame(
        columns=["supplier_id", "supplier_name", "latitude", "longitude", "capacity_units_month"]
    ).astype({
        "supplier_id": str,
        "supplier_name": str,
        "latitude": float,
        "longitude": float,
        "capacity_units_month": float,
    })
    fac = pd.DataFrame(
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "fixed_cost_dzd_month",
            "variable_cost_dzd_per_unit",
            "max_capacity_units",
            "is_existing",
        ]
    ).astype({
        "facility_id": str,
        "facility_name": str,
        "latitude": float,
        "longitude": float,
        "fixed_cost_dzd_month": float,
        "variable_cost_dzd_per_unit": float,
        "max_capacity_units": float,
        "is_existing": int,
    })
    return reg, sup, fac


def load_demo_data():
    reg = load_regions("data/example_algeria.csv")
    sup = load_suppliers("data/suppliers_example.csv")
    fac = load_facilities("data/facilities_example.csv")
    return reg, sup, fac


# Session state initialization: start completely blank by default
if "current_step" not in st.session_state:
    st.session_state.current_step = "data_studio"

if "regions_df" not in st.session_state or st.session_state.regions_df is None:
    r, s, f = get_empty_datasets()
    st.session_state.regions_df = r
    st.session_state.suppliers_df = s
    st.session_state.facilities_df = f
    st.session_state.custom_transport_df = None

st.markdown('<div class="main-title">Supply Chain Network Optimizer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">Two-Echelon Facility Location and Total Landed Cost Decision Cockpit</div>',
    unsafe_allow_html=True,
)

# Header navigation pills (only displayed during Step 1 Data Studio)
if st.session_state.current_step == "data_studio":
    nav_col1, nav_col2, _ = st.columns([1.5, 2, 4])
    with nav_col1:
        if st.button("Step 1: Data Studio & Ingestion", use_container_width=True):
            st.session_state.current_step = "data_studio"
            st.rerun()

    with nav_col2:
        if st.button("Step 2: Network Optimization Cockpit", use_container_width=True):
            st.session_state.current_step = "optimization_dashboard"
            st.rerun()

    st.markdown("---")
else:
    st.markdown("<hr style='margin: 0.8rem 0 1.2rem 0; border: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

# ==============================================================================
# STEP 1: DATA STUDIO
# ==============================================================================
if st.session_state.current_step == "data_studio":
    has_data = (
        st.session_state.regions_df is not None
        and not st.session_state.regions_df.empty
        and st.session_state.suppliers_df is not None
        and not st.session_state.suppliers_df.empty
        and st.session_state.facilities_df is not None
        and not st.session_state.facilities_df.empty
    )

    # Visual Process Pipeline
    arrow_svg = """<div class="pipeline-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="#1f4e78" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>"""
    
    st.markdown(
        f"""
        <div class="pipeline-container">
            <div class="pipeline-step {'active' if not has_data else ''}">
                <div class="step-tag">Step 1</div>
                <div class="step-title">Data Ingestion</div>
                <div class="step-desc">Auto-fill or upload CSV</div>
            </div>
            {arrow_svg}
            <div class="pipeline-step {'active' if has_data else ''}">
                <div class="step-tag">Step 2</div>
                <div class="step-title">Capacity Audit</div>
                <div class="step-desc">Supply vs Market Demand</div>
            </div>
            {arrow_svg}
            <div class="pipeline-step">
                <div class="step-tag">Step 3</div>
                <div class="step-title">MILP Optimization</div>
                <div class="step-desc">Google OR-Tools solver</div>
            </div>
            {arrow_svg}
            <div class="pipeline-step">
                <div class="step-tag">Step 4</div>
                <div class="step-title">Executive Cockpit</div>
                <div class="step-desc">Map, Landed Cost, N-1 Risk</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Methodology & Quick Start Guide", expanded=False):
        g_c1, g_c2 = st.columns(2)
        with g_c1:
            st.markdown(
                """
                <div class="guide-card">
                    <div class="guide-title">1. How to Initialize Your Network</div>
                    <div class="guide-text">
                        - <b>Benchmark Dataset:</b> Click <code>Auto-fill Demo Dataset (Algeria)</code> to load 12 regional demand centers, 2 gateway supply ports (Algiers, Bejaia), and 4 candidate distribution hubs.<br>
                        - <b>Custom Files:</b> Expand <code>Import Datasets via CSV Files</code> to upload enterprise operational data.<br>
                        - <b>In-Place Editing:</b> All table records below are editable directly (capacities, GPS coordinates, fixed overhead, and handling rates).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with g_c2:
            st.markdown(
                """
                <div class="guide-card">
                    <div class="guide-title">2. Network Feasibility & Transport Engine</div>
                    <div class="guide-text">
                        - <b>Supply Equilibrium:</b> Combined port throughput capacity and warehouse capacities must be greater than or equal to total market demand to prevent mathematical infeasibility.<br>
                        - <b>Geodesic Road Engine:</b> Road distances are computed using the Haversine formula scaled by a 1.25 terrain circuity factor to reflect commercial highway routing.<br>
                        - <b>Freight Tariff:</b> Default transport rate is 0.15 DZD per unit-kilometer.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    action_col1, action_col2, action_col3, _ = st.columns([2.4, 2.0, 2.2, 2.4])
    with action_col1:
        if st.button("Auto-fill Demo Dataset (Algeria)", type="primary", use_container_width=True):
            r, s, f = load_demo_data()
            st.session_state.regions_df = r
            st.session_state.suppliers_df = s
            st.session_state.facilities_df = f
            st.session_state.custom_transport_df = None
            st.success("Loaded Algeria benchmark dataset into editable tables.")
            st.rerun()

    with action_col2:
        if st.button("Reset / Clear Tables", type="secondary", use_container_width=True):
            r, s, f = get_empty_datasets()
            st.session_state.regions_df = r
            st.session_state.suppliers_df = s
            st.session_state.facilities_df = f
            st.session_state.custom_transport_df = None
            st.info("Data tables cleared.")
            st.rerun()

    has_data = (
        not st.session_state.regions_df.empty
        and not st.session_state.suppliers_df.empty
        and not st.session_state.facilities_df.empty
    )

    with action_col3:
        if st.button("Launch Optimization ->", type="secondary" if not has_data else "primary", use_container_width=True):
            if not has_data:
                st.warning("Data tables are empty. Add records, upload CSVs, or click Auto-fill Demo Dataset.")
            else:
                st.session_state.current_step = "optimization_dashboard"
                st.rerun()

    if not has_data:
        st.info(
            "The configuration tables are currently blank. Click 'Auto-fill Demo Dataset (Algeria)' above, "
            "import CSV files, or add rows directly to the tables below."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Optional CSV upload expander
    with st.expander("Import Datasets via CSV Files", expanded=False):
        up_col1, up_col2, up_col3, up_col4 = st.columns(4)
        with up_col1:
            u_reg = st.file_uploader("Regional Demand CSV", type=["csv"], key="u_reg")
        with up_col2:
            u_sup = st.file_uploader("Supply Gateways CSV", type=["csv"], key="u_sup")
        with up_col3:
            u_fac = st.file_uploader("Candidate DCs CSV", type=["csv"], key="u_fac")
        with up_col4:
            u_trans = st.file_uploader("Transport Matrix CSV (Optional)", type=["csv"], key="u_trans")

        if st.button("Apply Uploaded Files", key="btn_apply_uploads"):
            try:
                if u_reg:
                    st.session_state.regions_df = load_regions(u_reg)
                if u_sup:
                    st.session_state.suppliers_df = load_suppliers(u_sup)
                if u_fac:
                    st.session_state.facilities_df = load_facilities(u_fac)
                if u_trans:
                    st.session_state.custom_transport_df = pd.read_csv(u_trans)
                st.success("Uploaded files successfully validated and loaded.")
                st.rerun()
            except Exception as e:
                st.error(f"Error parsing uploaded file: {e}")

    # Editable Data Tables
    tab_r, tab_s, tab_f = st.tabs([
        "1. Regional Demand Markets",
        "2. Supply Ports & Gateways",
        "3. Candidate Distribution Centers",
    ])

    with tab_r:
        st.caption("Add, remove, or adjust regional demand volumes and coordinates.")
        edited_regions = st.data_editor(
            st.session_state.regions_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_regions",
        )
        st.session_state.regions_df = edited_regions

    with tab_s:
        st.caption("Define upstream supply ports and maximum monthly throughput limits.")
        edited_suppliers = st.data_editor(
            st.session_state.suppliers_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_suppliers",
        )
        st.session_state.suppliers_df = edited_suppliers

    with tab_f:
        st.caption("Specify candidate DC sites, leasing overhead, handling fees, and capacities.")
        edited_facilities = st.data_editor(
            st.session_state.facilities_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_facilities",
        )
        st.session_state.facilities_df = edited_facilities

    # Integrity & Capacity Sanity Check
    tot_dem = float(st.session_state.regions_df["demand_units_month"].sum()) if not st.session_state.regions_df.empty else 0.0
    tot_sup = float(st.session_state.suppliers_df["capacity_units_month"].sum()) if not st.session_state.suppliers_df.empty else 0.0
    tot_fac = float(st.session_state.facilities_df["max_capacity_units"].sum()) if not st.session_state.facilities_df.empty else 0.0

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Network Capacity & Feasibility Check")
    chk1, chk2, chk3, chk4 = st.columns(4)

    chk1.metric("Total Monthly Demand", f"{tot_dem:,.0f} units")
    chk2.metric("Total Supply Gateway Capacity", f"{tot_sup:,.0f} units", delta=f"{tot_sup - tot_dem:,.0f} surplus" if tot_sup >= tot_dem else "DEFICIT")
    chk3.metric("Total Candidate DC Capacity", f"{tot_fac:,.0f} units", delta=f"{tot_fac - tot_dem:,.0f} surplus" if tot_fac >= tot_dem else "DEFICIT")
    
    with chk4:
        st.write("")
        if st.button("Proceed to Optimization ->", type="primary", use_container_width=True, key="btn_proceed"):
            st.session_state.current_step = "optimization_dashboard"
            st.rerun()

# ==============================================================================
# STEP 2: OPTIMIZATION DASHBOARD
# ==============================================================================
elif st.session_state.current_step == "optimization_dashboard":
    has_data = (
        st.session_state.regions_df is not None
        and not st.session_state.regions_df.empty
        and st.session_state.suppliers_df is not None
        and not st.session_state.suppliers_df.empty
        and st.session_state.facilities_df is not None
        and not st.session_state.facilities_df.empty
    )
    if not has_data:
        st.warning("No data has been loaded yet. Please configure or auto-fill your datasets in Step 1.")
        if st.button("<- Return to Data Studio"):
            st.session_state.current_step = "data_studio"
            st.rerun()
        st.stop()

    # Validate tables from session state before running
    try:
        validated_regions = []
        for _, r in st.session_state.regions_df.iterrows():
            rec = RegionSchema(
                region_id=str(r["region_id"]).strip(),
                region_name=str(r["region_name"]).strip(),
                latitude=float(r["latitude"]),
                longitude=float(r["longitude"]),
                demand_units_month=float(r["demand_units_month"]),
            )
            validated_regions.append(rec.model_dump())
        v_reg_df = pd.DataFrame(validated_regions)

        validated_suppliers = []
        for _, s in st.session_state.suppliers_df.iterrows():
            s_rec = SupplierSchema(
                supplier_id=str(s["supplier_id"]).strip(),
                supplier_name=str(s["supplier_name"]).strip(),
                latitude=float(s["latitude"]),
                longitude=float(s["longitude"]),
                capacity_units_month=float(s["capacity_units_month"]),
            )
            validated_suppliers.append(s_rec.model_dump())
        v_sup_df = pd.DataFrame(validated_suppliers)

        validated_facilities = []
        for _, f in st.session_state.facilities_df.iterrows():
            f_rec = FacilitySchema(
                facility_id=str(f["facility_id"]).strip(),
                facility_name=str(f["facility_name"]).strip(),
                latitude=float(f["latitude"]),
                longitude=float(f["longitude"]),
                fixed_cost_dzd_month=float(f["fixed_cost_dzd_month"]),
                variable_cost_dzd_per_unit=float(f["variable_cost_dzd_per_unit"]),
                max_capacity_units=float(f["max_capacity_units"]),
                is_existing=int(f.get("is_existing", 0)),
            )
            validated_facilities.append(f_rec.model_dump())
        v_fac_df = pd.DataFrame(validated_facilities)

    except Exception as err:
        st.error(f"Input validation error in data tables: {err}")
        if st.button("<- Return to Data Studio"):
            st.session_state.current_step = "data_studio"
            st.rerun()
        st.stop()

    # Sidebar: Currency and Sensitivity Controls
    st.sidebar.button("<- Back to Data Setup", on_click=lambda: st.session_state.update(current_step="data_studio"))
    st.sidebar.markdown("---")
    st.sidebar.subheader("Reporting Currency")

    currency_choice = st.sidebar.selectbox(
        "Target Display Currency",
        DEFAULT_CURRENCY_CONFIG.supported_currencies,
        index=0,
    )

    fx_rates: Dict[str, float] = {"DZD": 1.0}
    if currency_choice in ("USD", "EUR"):
        col_fx1, col_fx2 = st.sidebar.columns(2)
        eur_rate = col_fx1.number_input("EUR / DZD", value=145.0, min_value=1.0, step=1.0)
        usd_rate = col_fx2.number_input("USD / DZD", value=134.0, min_value=1.0, step=1.0)
        fx_rates["EUR"] = float(eur_rate)
        fx_rates["USD"] = float(usd_rate)
    else:
        fx_rates["EUR"] = 145.0
        fx_rates["USD"] = 134.0

    st.sidebar.markdown("---")
    st.sidebar.subheader("Sensitivity Analysis Sliders")

    demand_mult = st.sidebar.slider(
        "Demand Volume Multiplier",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Simulate aggregate market demand fluctuations.",
    )

    freight_mult = st.sidebar.slider(
        "Freight Rate Index Multiplier",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Simulate fuel price shifts or transport tariff inflation.",
    )

    fixed_cost_mult = st.sidebar.slider(
        "Facility Overhead Multiplier",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Simulate real estate leasing and warehouse fixed overhead variation.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Operational Constraints")

    enforce_existing = st.sidebar.checkbox(
        "Lock Existing Warehouses Active",
        value=False,
        help="Forces currently operating distribution centers to remain open.",
    )

    limit_lead_time = st.sidebar.checkbox(
        "Enforce Delivery SLA Ceiling",
        value=False,
        help="Constrain allocations to maximum allowable delivery days.",
    )

    max_sla_days: Optional[int] = None
    if limit_lead_time:
        max_sla_days = st.sidebar.slider("Maximum Delivery Lead Time (Days)", 1, 6, 2)

    with st.sidebar.expander("Understanding Operational Parameters", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.80rem; color: #334155; line-height: 1.4;">
                <b>Sensitivity Analysis Sliders:</b><br>
                - <b>Demand Multiplier:</b> Simulates macroeconomic demand shifts (+/- 50% or seasonal surges).<br>
                - <b>Freight Rate Index:</b> Evaluates exposure to diesel fuel price inflation or carrier rate renegotiations.<br>
                - <b>Facility Overhead:</b> Models warehouse leasing escalation and labor overhead inflation.<br><br>
                <b>Operational Constraints:</b><br>
                - <b>Lock Existing Active:</b> Brownfield industrial constraint forcing operating sites to remain open.<br>
                - <b>Delivery SLA Ceiling:</b> Strict transit ceiling (days) that forbids allocations exceeding the threshold.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Matrix synthesis
    inbound_costs, outbound_costs, lead_times, distances_km = synthesize_transport_matrices(
        regions=v_reg_df,
        suppliers=v_sup_df,
        facilities=v_fac_df,
        custom_transport_df=st.session_state.custom_transport_df,
        config=DEFAULT_OPERATIONAL_CONFIG,
    )

    # Solve MILP
    with st.spinner("Solving network allocation with Google OR-Tools..."):
        opt_result = solve_facility_location(
            regions=v_reg_df,
            suppliers=v_sup_df,
            facilities=v_fac_df,
            inbound_costs=inbound_costs,
            outbound_costs=outbound_costs,
            lead_times=lead_times,
            max_lead_time_days=max_sla_days,
            enforce_existing_facilities=enforce_existing,
            demand_multiplier=demand_mult,
            transport_cost_multiplier=freight_mult,
            fixed_cost_multiplier=fixed_cost_mult,
            solver_time_limit_seconds=DEFAULT_OPERATIONAL_CONFIG.solver_time_limit_seconds,
        )

    if not opt_result.is_feasible:
        st.error(
            f"Optimization status: {opt_result.solver_status}. "
            "The network configuration is infeasible under current constraints. "
            "Check total supplier throughput capacity, facility limits, or SLA day threshold."
        )
        if st.button("<- Return to Data Setup"):
            st.session_state.current_step = "data_studio"
            st.rerun()
        st.stop()

    converted_costs = convert_costs_to_currency(
        breakdown=opt_result.cost_breakdown,
        total_demand=opt_result.kpis.total_demand,
        target_currency=currency_choice,
        custom_fx_rates=fx_rates,
    )

    baseline_stats = compute_baseline_status_quo(
        regions=v_reg_df,
        suppliers=v_sup_df,
        facilities=v_fac_df,
        inbound_costs=inbound_costs,
        outbound_costs=outbound_costs,
        lead_times=lead_times,
        target_currency=currency_choice,
        custom_fx_rates=fx_rates,
    )

    baseline_comp = compare_with_baseline(
        result=opt_result,
        baseline_stats=baseline_stats,
        target_currency=currency_choice,
        custom_fx_rates=fx_rates,
    )

    # Advanced Enterprise Calculations
    # 1. Greenfield Continuous Center of Gravity (Weiszfeld)
    greenfield_centroid = compute_weiszfeld_centroid(v_reg_df)

    # 2. Scope 3 Carbon Emissions (GHG Accounting)
    base_sup_id = str(v_sup_df.iloc[0]["supplier_id"])
    base_fac_id = baseline_stats["primary_facility_id"]
    unit_wt_tonnes = 10.0 / 1000.0
    base_tot_dem = float(v_reg_df["demand_units_month"].sum())
    base_tkm = base_tot_dem * unit_wt_tonnes * distances_km.get((base_sup_id, base_fac_id), 0.0)
    for _, r in v_reg_df.iterrows():
        d_km = distances_km.get((base_fac_id, str(r["region_id"])), 0.0)
        base_tkm += float(r["demand_units_month"]) * unit_wt_tonnes * d_km
    baseline_stats["baseline_total_tkm"] = base_tkm

    carbon_report = calculate_transport_emissions(
        inbound_flows=opt_result.inbound_flows,
        assignments=opt_result.assignments,
        distances_km=distances_km,
        unit_weight_kg=10.0,
        emission_factor_kg_per_tkm=0.070,
        baseline_stats=baseline_stats,
    )

    # 3. Working Capital & Safety Stock (Square Root Law)
    inventory_report = calculate_safety_stock_holding(
        open_facility_count=opt_result.kpis.open_facility_count,
        total_monthly_demand=opt_result.kpis.total_demand,
        safety_stock_coverage_days=14.0,
        inventory_unit_value_dzd=1200.0,
        annual_carrying_rate_pct=18.0,
    )

    # Executive Metric Cards (6 Columns)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Total Landed Cost</div>
                <div class="metric-val">{converted_costs.symbol} {converted_costs.total_landed_cost:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        savings_color = "#2ca02c" if baseline_comp.absolute_savings >= 0 else "#d95f02"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Net Savings vs Baseline</div>
                <div class="metric-val" style="color: {savings_color};">
                    {converted_costs.symbol} {baseline_comp.absolute_savings:,.0f}
                    <span style="font-size: 0.85rem; font-weight: normal;">({baseline_comp.percentage_savings:.1f}%)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Active Distribution Hubs</div>
                <div class="metric-val">{opt_result.kpis.open_facility_count} of {len(opt_result.facilities)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Weighted Lead Time</div>
                <div class="metric-val">
                    {opt_result.kpis.weighted_average_lead_time_days:.2f} d
                    <span style="font-size: 0.85rem; color: #2ca02c; font-weight: normal;">
                        (-{baseline_comp.lead_time_reduction_days:.1f} d)
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Unit Landed Cost</div>
                <div class="metric-val">{converted_costs.symbol} {converted_costs.cost_per_unit:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col6:
        co2_delta_str = (
            f"(-{carbon_report.co2_savings_percentage:.1f}%)"
            if carbon_report.co2_savings_percentage is not None
            else ""
        )
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Scope 3 Emissions</div>
                <div class="metric-val">
                    {carbon_report.total_co2_tonnes:.1f} t
                    <span style="font-size: 0.85rem; color: #2ca02c; font-weight: normal;">
                        {co2_delta_str}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Detailed Analysis Tabs
    (
        tab_map,
        tab_costs,
        tab_facs,
        tab_assign,
        tab_inflow,
        tab_sensitivity,
        tab_resilience,
    ) = st.tabs([
        "Interactive Network Topology",
        "Landed Cost Breakdown",
        "Distribution Centers",
        "Customer Market Allocation",
        "Upstream Inflow",
        "What-If Sensitivity Scenarios",
        "N-1 Crisis Resilience & Stress-Test",
    ])

    with tab_map:
        st.subheader("Optimal Network Design and Freight Routing")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            show_sla_coverage = st.checkbox("Display 24h & 48h Delivery SLA Coverage Radii", value=True)
        with col_m2:
            show_greenfield = st.checkbox("Display Greenfield Optimal Centroid (Weiszfeld)", value=True)

        st.info(
            f"Greenfield Center of Gravity Discovery (Weiszfeld Continuous Optimization): "
            f"Theoretical optimal demand-weighted coordinates: ({greenfield_centroid.optimal_latitude}, {greenfield_centroid.optimal_longitude}) "
            f"located {greenfield_centroid.distance_to_nearest_km:.1f} km from {greenfield_centroid.nearest_region_name}. "
            f"Weighted average transport radius: {greenfield_centroid.weighted_average_distance_km:.1f} km."
        )

        fmap = create_network_map(
            result=opt_result,
            suppliers_df=v_sup_df,
            facilities_df=v_fac_df,
            regions_df=v_reg_df,
            show_service_coverage=show_sla_coverage,
            greenfield_centroid=greenfield_centroid if show_greenfield else None,
        )
        with st.expander("Cartographic Guide: SLA Delivery Radii & Greenfield Centroid", expanded=False):
            st.markdown(
                """
                <div class="guide-card">
                    <div class="guide-title">Cartographic Guide & Analytical Indicators</div>
                    <div class="guide-text">
                        - <b>Delivery SLA Radii (Service Coverage Zones):</b><br>
                          &bull; <i>Green Zone (250 km):</i> Guaranteed <b>24-hour</b> expedited transit perimeter around active distribution centers.<br>
                          &bull; <i>Amber Zone (500 km):</i> Standard <b>48-hour</b> regional service perimeter.<br>
                          &bull; <i>Markets Outside Circles:</i> Remote customer regions requiring 3 or more transit days.<br><br>
                        - <b>Greenfield Centroid (Red Target Marker - Weiszfeld):</b><br>
                          Continuous spatial optimization balance point representing the optimal demand-weighted coordinates. It serves as an executive benchmark: candidate distribution centers located closer to this theoretical center minimize aggregate road freight ton-kilometers.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st_folium(fmap, use_container_width=True, height=560)

    with tab_costs:
        col_chart, col_tbl = st.columns([3, 2])
        with col_chart:
            pie_fig = plot_cost_breakdown_pie(converted_costs)
            st.plotly_chart(pie_fig, use_container_width=True)

        with col_tbl:
            st.subheader("Financial Component Decomposition")
            cost_df = pd.DataFrame([
                {"Component": "Fixed Facility Overhead", f"Amount ({converted_costs.currency})": f"{converted_costs.fixed_facility_cost:,.2f}"},
                {"Component": "Variable Handling Expenditure", f"Amount ({converted_costs.currency})": f"{converted_costs.variable_handling_cost:,.2f}"},
                {"Component": "Inbound Primary Freight", f"Amount ({converted_costs.currency})": f"{converted_costs.inbound_freight_cost:,.2f}"},
                {"Component": "Outbound Secondary Freight", f"Amount ({converted_costs.currency})": f"{converted_costs.outbound_freight_cost:,.2f}"},
                {"Component": "TOTAL LANDED COST", f"Amount ({converted_costs.currency})": f"{converted_costs.total_landed_cost:,.2f}"},
            ])
            st.dataframe(cost_df, hide_index=True, use_container_width=True)

            st.subheader("Status Quo Baseline Comparison")
            comp_df = pd.DataFrame([
                {"Metric": "Status Quo (Single DC Baseline)", "Value": f"{converted_costs.symbol} {baseline_comp.baseline_total_cost:,.2f}"},
                {"Metric": "Optimal Network Cost", "Value": f"{converted_costs.symbol} {baseline_comp.optimized_total_cost:,.2f}"},
                {"Metric": "Net Annual Savings", "Value": f"{converted_costs.symbol} {baseline_comp.absolute_savings:,.2f} ({baseline_comp.percentage_savings:.1f}%)"},
                {"Metric": "Average Transit Time Reduction", "Value": f"{baseline_comp.lead_time_reduction_days:.1f} day(s)"},
            ])
            st.dataframe(comp_df, hide_index=True, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Working Capital & Safety Stock Centralization (Eppen-Maister Law)")
        st.write("Models the inventory centralization trade-off: decentralized hubs reduce transport costs but expand safety stock holdings.")
        inv_col1, inv_col2, inv_col3, inv_col4 = st.columns(4)
        inv_col1.metric("Centralized Safety Stock (1 DC)", f"{inventory_report.centralized_safety_stock_units:,.0f} units")
        inv_col2.metric("Decentralized Safety Stock", f"{inventory_report.decentralized_safety_stock_units:,.0f} units", delta=f"+{inventory_report.safety_stock_expansion_percentage:.1f}% expansion")
        inv_col3.metric(f"Monthly Holding Cost ({converted_costs.currency})", f"{inventory_report.monthly_holding_cost_dzd / converted_costs.exchange_rate:,.2f}")
        inv_col4.metric(f"Centralization Penalty vs 1 DC ({converted_costs.currency})", f"{inventory_report.centralization_penalty_monthly_dzd / converted_costs.exchange_rate:,.2f}")

    with tab_facs:
        st.subheader("Facility Operational Capacity and Utilization")
        util_fig = plot_facility_utilization(opt_result.facilities)
        st.plotly_chart(util_fig, use_container_width=True)

        fac_rows = [
            {
                "Facility ID": f.facility_id,
                "Facility Name": f.facility_name,
                "Decision": "OPEN" if f.is_open else "CLOSED",
                "Throughput (units)": f"{f.assigned_throughput:,.0f}",
                "Max Capacity (units)": f"{f.max_capacity:,.0f}",
                "Utilization Rate": f"{f.utilization_rate * 100.0:.1f}%",
                f"Fixed Overhead ({converted_costs.currency})": f"{f.fixed_cost / converted_costs.exchange_rate:,.2f}",
                f"Variable Handling ({converted_costs.currency})": f"{f.variable_cost / converted_costs.exchange_rate:,.2f}",
            }
            for f in opt_result.facilities
        ]
        st.dataframe(pd.DataFrame(fac_rows), hide_index=True, use_container_width=True)

    with tab_assign:
        st.subheader("Regional Customer Market Assignments")
        assign_rows = [
            {
                "Region ID": a.region_id,
                "Customer Market": a.region_name,
                "Assigned DC ID": a.serving_facility_id,
                "Assigned DC Name": a.serving_facility_name,
                "Demand Served (units)": f"{a.demand_served:,.0f}",
                "Transit Lead Time (days)": a.lead_time_days,
                f"Unit Freight ({converted_costs.currency})": f"{a.outbound_unit_cost / converted_costs.exchange_rate:,.4f}",
                f"Total Outbound Freight ({converted_costs.currency})": f"{a.outbound_total_cost / converted_costs.exchange_rate:,.2f}",
            }
            for a in opt_result.assignments
        ]
        st.dataframe(pd.DataFrame(assign_rows), hide_index=True, use_container_width=True)

    with tab_inflow:
        st.subheader("Inbound Port Replenishment Allocations")
        inflow_rows = [
            {
                "Supply Gateway ID": fl.supplier_id,
                "Supply Gateway": fl.supplier_name,
                "Destination DC ID": fl.facility_id,
                "Destination DC": fl.facility_name,
                "Inflow Volume (units)": f"{fl.volume_units:,.0f}",
                f"Unit Inbound Freight ({converted_costs.currency})": f"{fl.unit_cost / converted_costs.exchange_rate:,.4f}",
                f"Total Inbound Freight ({converted_costs.currency})": f"{fl.total_cost / converted_costs.exchange_rate:,.2f}",
            }
            for fl in opt_result.inbound_flows
        ]
        st.dataframe(pd.DataFrame(inflow_rows), hide_index=True, use_container_width=True)

    with tab_sensitivity:
        st.subheader("Automated What-If Sensitivity Scenarios")
        st.write("Evaluates pre-configured operational stress tests against the current baseline.")

        scenarios = [
            ("Baseline (1.0x)", 1.0, 1.0, 1.0),
            ("High Fuel (+30% Freight)", 1.0, 1.3, 1.0),
            ("Peak Demand (+20% Volume)", 1.2, 1.0, 1.0),
            ("Overhead Surge (+25% Fixed)", 1.0, 1.0, 1.25),
            ("Combined Stress (+20% Dem, +20% Freight)", 1.2, 1.2, 1.0),
        ]

        scen_names = []
        scen_costs = []
        scen_lts = []
        scen_dcs = []

        for name, d_m, t_m, f_m in scenarios:
            res = solve_facility_location(
                regions=v_reg_df,
                suppliers=v_sup_df,
                facilities=v_fac_df,
                inbound_costs=inbound_costs,
                outbound_costs=outbound_costs,
                lead_times=lead_times,
                demand_multiplier=d_m,
                transport_cost_multiplier=t_m,
                fixed_cost_multiplier=f_m,
            )
            if res.is_feasible:
                converted = convert_costs_to_currency(
                    breakdown=res.cost_breakdown,
                    total_demand=res.kpis.total_demand,
                    target_currency=currency_choice,
                    custom_fx_rates=fx_rates,
                )
                scen_names.append(name)
                scen_costs.append(converted.total_landed_cost)
                scen_lts.append(res.kpis.weighted_average_lead_time_days)
                scen_dcs.append(res.kpis.open_facility_count)

        scen_fig = plot_scenario_comparison(
            scenario_names=scen_names,
            total_costs=scen_costs,
            lead_times=scen_lts,
            currency_symbol=converted_costs.symbol,
        )
        st.plotly_chart(scen_fig, use_container_width=True)

        scen_table_data = [
            {
                "Scenario": n,
                f"Total Landed Cost ({converted_costs.currency})": f"{c:,.2f}",
                "Avg Transit (days)": f"{lt:.2f}",
                "Active Hubs": d,
            }
            for n, c, lt, d in zip(scen_names, scen_costs, scen_lts, scen_dcs)
        ]
        st.dataframe(pd.DataFrame(scen_table_data), hide_index=True, use_container_width=True)

    with tab_resilience:
        st.subheader("N-1 Supply Chain Crisis and Disruption Contingency Simulator")
        st.write("Stress-test the resilience of the network by disabling an active gateway port or distribution center.")

        with st.expander("N-1 Disruption Simulation Methodology Guide", expanded=False):
            st.markdown(
                """
                <div class="guide-card">
                    <div class="guide-title">Principles of N-1 Contingency Stress-Testing</div>
                    <div class="guide-text">
                        - <b>Objective:</b> Measure supply chain vulnerability by simulating the catastrophic shutdown of a critical node (gateway port closure, labor action, severe weather, or warehouse loss).<br>
                        - <b>Dynamic Contingency Re-Optimization:</b> The OR-Tools MILP solver disables the target node and re-solves the degraded network in real time across surviving infrastructure.<br>
                        - <b>Executive Risk Metrics:</b><br>
                          &bull; <i>Network Resilience Score (0 to 100):</i> Quantitative score evaluating how effectively the network absorbs the outage without runaway freight inflation or severe delay spikes.<br>
                          &bull; <i>Financial Cost Surge:</i> Landed cost inflation caused by detour miles and expedited carrier re-allocations.<br>
                          &bull; <i>Lead Time Delta:</i> Average delivery delay increase across regional customer markets.<br>
                          &bull; <i>Emergency Reassignments:</i> Exact list of regional customer markets transferred to alternative distribution hubs.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        res_col1, res_col2, res_col3 = st.columns([1.5, 2.5, 1.5], vertical_alignment="bottom")
        with res_col1:
            disrupt_type = st.radio("Disruption Node Category", ["Supplier Port", "Distribution Center"], index=0)

        with res_col2:
            if disrupt_type == "Supplier Port":
                node_options = {f"{r['supplier_name']} ({r['supplier_id']})": str(r["supplier_id"]) for _, r in v_sup_df.iterrows()}
            else:
                node_options = {f"{r['facility_name']} ({r['facility_id']})": str(r["facility_id"]) for _, r in v_fac_df.iterrows()}
            selected_label = st.selectbox("Select Node to Disclose as Inaccessible", list(node_options.keys()))
            selected_node_id = node_options[selected_label]

        with res_col3:
            run_disrupt = st.button("Simulate N-1 Disruption", type="primary", use_container_width=True)

        if run_disrupt:
            with st.spinner("Re-solving contingency network..."):
                t_type = "supplier" if disrupt_type == "Supplier Port" else "facility"
                disrupt_res = simulate_single_node_disruption(
                    node_id=selected_node_id,
                    node_type=t_type,
                    regions=v_reg_df,
                    suppliers=v_sup_df,
                    facilities=v_fac_df,
                    inbound_costs=inbound_costs,
                    outbound_costs=outbound_costs,
                    lead_times=lead_times,
                    base_optimal_result=opt_result,
                )

            if not disrupt_res.is_feasible_contingency:
                st.error(f"CRITICAL SYSTEM FAILURE: Network is INFEASIBLE if '{disrupt_res.disrupted_node_name}' is disabled.")

                tot_dem = float(v_reg_df["demand_units_month"].sum())
                if t_type == "supplier":
                    rem_cap = float(v_sup_df[v_sup_df["supplier_id"] != selected_node_id]["capacity_units_month"].sum())
                    node_label = "surviving gateway ports"
                else:
                    rem_cap = float(v_fac_df[v_fac_df["facility_id"] != selected_node_id]["max_capacity_units"].sum())
                    node_label = "surviving distribution centers"

                deficit = tot_dem - rem_cap
                st.markdown(
                    f"""
                    <div class="guide-card" style="border-left-color: #d9534f; background-color: #fff8f8;">
                        <div class="guide-title" style="color: #c9302c;">Disruption Diagnostic & Risk Analysis (Single Point of Failure - SPOF)</div>
                        <div class="guide-text">
                            - <b>Total Market Demand to Serve:</b> {tot_dem:,.0f} units/month<br>
                            - <b>Available Residual Capacity ({node_label}):</b> {rem_cap:,.0f} units/month<br>
                            - <b>Net Physical Deficit:</b> <span style="color: #c9302c; font-weight: bold;">{deficit:,.0f} units/month ({deficit / tot_dem * 100:.1f}% unfulfilled market demand)</span><br><br>
                            <b>Operational Finding:</b> This facility represents a <b>Single Point of Failure (SPOF)</b>. Without it, surviving infrastructure cannot physically absorb total market demand. The solver flags infeasibility because the requirement to serve 100% of customer orders cannot be fulfilled.<br><br>
                            <b>Executive Supply Chain Recommendations:</b>
                            <ol style="margin-bottom: 0; padding-left: 20px;">
                                <li>Contract expanded throughput capacity on alternate facilities to guarantee at least {tot_dem:,.0f} units/month.</li>
                                <li>Qualify an additional backup supply gateway (e.g., Port of Oran or Port of Djen Djen) to diversify maritime risk exposure.</li>
                            </ol>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.success(f"Contingency feasible: The network successfully absorbs the outage of {disrupt_res.disrupted_node_name}.")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Network Resilience Score", f"{disrupt_res.resilience_score:.1f} / 100")
                m2.metric(f"Contingency Cost ({converted_costs.currency})", f"{disrupt_res.contingency_cost_dzd / converted_costs.exchange_rate:,.0f}")
                m3.metric(f"Financial Cost Surge ({converted_costs.currency})", f"+{disrupt_res.cost_surge_dzd / converted_costs.exchange_rate:,.0f} (+{disrupt_res.cost_surge_percentage:.1f}%)")
                m4.metric("Contingency Avg Lead Time", f"{disrupt_res.contingency_lead_time_days:.2f} d", delta=f"+{disrupt_res.lead_time_delta_days:.2f} d delay")

                if disrupt_res.emergency_reassignments:
                    st.subheader("Emergency Customer Market Reassignments")
                    st.dataframe(pd.DataFrame(disrupt_res.emergency_reassignments), hide_index=True, use_container_width=True)
                else:
                    st.info("No regional customer reassignments were required under this contingency scenario.")

    # Export Section
    st.markdown("---")
    st.subheader("Report Export")

    excel_buffer = generate_excel_report(
        result=opt_result,
        currency_breakdown=converted_costs,
        baseline_comparison=baseline_comp,
    )

    st.download_button(
        label=f"Download Executive Audit Report ({currency_choice} Excel)",
        data=excel_buffer.getvalue(),
        file_name=f"SCNO_Executive_Report_{currency_choice}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
