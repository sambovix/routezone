"""Interactive geospatial mapping and financial visualization."""

from typing import Any, Dict, List, Optional
import folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.network_analyzer import CurrencyConvertedBreakdown
from src.optimizer import FacilityStatus, OptimizationResult


def create_network_map(
    result: OptimizationResult,
    suppliers_df,
    facilities_df,
    regions_df,
    center_lat: float = 36.0,
    center_lon: float = 3.5,
    zoom_start: int = 6,
    show_service_coverage: bool = True,
    greenfield_centroid: Optional[Any] = None,
) -> folium.Map:
    """Build interactive Folium map rendering network topology and allocations.

    Visual encoding:
        - Supply Port Gateways: Blue diamond markers
        - Open Distribution Centers: Green warehouse markers with throughput popup
        - Closed Facilities: Gray markers
        - Demand Regions: Orange circle markers with radius scaled to demand
        - Upstream Inflow Arcs: Blue dashed polylines
        - Downstream Distribution Arcs: Green solid polylines (weight scaled to volume)

    Args:
        result: Solved network optimization output.
        suppliers_df: Suppliers DataFrame.
        facilities_df: Candidate facilities DataFrame.
        regions_df: Demand regions DataFrame.
        center_lat: Initial map center latitude.
        center_lon: Initial map center longitude.
        zoom_start: Initial zoom level.

    Returns:
        folium.Map instance.
    """
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
    )

    # 1. Plot Supply Gateways
    for _, sup in suppliers_df.iterrows():
        s_id = str(sup["supplier_id"])
        s_name = str(sup["supplier_name"])
        s_lat = float(sup["latitude"])
        s_lon = float(sup["longitude"])
        s_cap = float(sup["capacity_units_month"])

        popup_html = (
            f"<b>Supplier Gateway:</b> {s_name} ({s_id})<br>"
            f"<b>Capacity:</b> {s_cap:,.0f} units/month"
        )
        folium.Marker(
            location=[s_lat, s_lon],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"Gateway: {s_name}",
            icon=folium.Icon(color="blue", icon="anchor", prefix="fa"),
        ).add_to(fmap)

    # 2. Plot Candidate Facilities
    fac_status_map: Dict[str, FacilityStatus] = {
        f.facility_id: f for f in result.facilities
    }

    for _, fac in facilities_df.iterrows():
        f_id = str(fac["facility_id"])
        f_name = str(fac["facility_name"])
        f_lat = float(fac["latitude"])
        f_lon = float(fac["longitude"])
        f_stat = fac_status_map.get(f_id)

        is_open = f_stat.is_open if f_stat else False
        util_pct = (f_stat.utilization_rate * 100.0) if f_stat else 0.0
        thru = f_stat.assigned_throughput if f_stat else 0.0
        cap = f_stat.max_capacity if f_stat else float(fac["max_capacity_units"])

        if is_open:
            color = "green"
            icon_name = "building"
            label = "OPEN DC"
        else:
            color = "lightgray"
            icon_name = "times"
            label = "CLOSED CANDIDATE"

        popup_html = (
            f"<b>{label}:</b> {f_name} ({f_id})<br>"
            f"<b>Status:</b> {'ACTIVE' if is_open else 'INACTIVE'}<br>"
            f"<b>Throughput:</b> {thru:,.0f} / {cap:,.0f} units ({util_pct:.1f}%)"
        )
        folium.Marker(
            location=[f_lat, f_lon],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{label}: {f_name}",
            icon=folium.Icon(color=color, icon=icon_name, prefix="fa"),
        ).add_to(fmap)

    # 3. Plot Inbound Supply Arcs
    for flow in result.inbound_flows:
        s_rows = suppliers_df[suppliers_df["supplier_id"] == flow.supplier_id]
        f_rows = facilities_df[facilities_df["facility_id"] == flow.facility_id]
        if not s_rows.empty and not f_rows.empty:
            s_lat = float(s_rows.iloc[0]["latitude"])
            s_lon = float(s_rows.iloc[0]["longitude"])
            f_lat = float(f_rows.iloc[0]["latitude"])
            f_lon = float(f_rows.iloc[0]["longitude"])

            arc_popup = (
                f"<b>Inbound Replenishment:</b><br>"
                f"{flow.supplier_name} -> {flow.facility_name}<br>"
                f"<b>Volume:</b> {flow.volume_units:,.0f} units"
            )
            folium.PolyLine(
                locations=[[s_lat, s_lon], [f_lat, f_lon]],
                color="#1f77b4",
                weight=3,
                dash_array="6",
                opacity=0.8,
                popup=folium.Popup(arc_popup, max_width=220),
            ).add_to(fmap)

    # 4. Plot Demand Regions and Outbound Distribution Arcs
    max_demand = float(regions_df["demand_units_month"].max()) if not regions_df.empty else 1.0

    for assign in result.assignments:
        r_lat = assign.region_latitude
        r_lon = assign.region_longitude
        f_lat = assign.facility_latitude
        f_lon = assign.facility_longitude

        # Circle marker sized to regional volume
        rad = 6 + (assign.demand_served / max_demand) * 14

        region_popup = (
            f"<b>Market:</b> {assign.region_name} ({assign.region_id})<br>"
            f"<b>Assigned DC:</b> {assign.serving_facility_name}<br>"
            f"<b>Demand:</b> {assign.demand_served:,.0f} units<br>"
            f"<b>Lead Time:</b> {assign.lead_time_days} day(s)"
        )
        folium.CircleMarker(
            location=[r_lat, r_lon],
            radius=rad,
            color="#e6550d",
            fill=True,
            fill_color="#fdae6b",
            fill_opacity=0.85,
            popup=folium.Popup(region_popup, max_width=220),
            tooltip=f"{assign.region_name} ({assign.demand_served:,.0f} units)",
        ).add_to(fmap)

        # Flow line from facility to customer market
        weight = max(1.5, min(6.0, (assign.demand_served / max_demand) * 5.0))
        folium.PolyLine(
            locations=[[f_lat, f_lon], [r_lat, r_lon]],
            color="#2ca02c",
            weight=weight,
            opacity=0.85,
            popup=folium.Popup(
                f"{assign.serving_facility_name} -> {assign.region_name}<br>"
                f"Transit: {assign.lead_time_days} day(s)",
                max_width=200,
            ),
        ).add_to(fmap)

    # 5. Plot SLA Delivery Service Radii around Open Distribution Centers
    if show_service_coverage:
        for f in result.facilities:
            if f.is_open:
                # 24-hour service radius: 250 km (250,000 meters)
                folium.Circle(
                    location=[f.latitude, f.longitude],
                    radius=250000,
                    color="#2ca02c",
                    fill=True,
                    fill_color="#2ca02c",
                    fill_opacity=0.06,
                    weight=1,
                    dash_array="5, 5",
                    tooltip=f"24h Delivery SLA Zone (250 km) - {f.facility_name}",
                ).add_to(fmap)

                # 48-hour service radius: 500 km (500,000 meters)
                folium.Circle(
                    location=[f.latitude, f.longitude],
                    radius=500000,
                    color="#ff7f00",
                    fill=True,
                    fill_color="#ff7f00",
                    fill_opacity=0.03,
                    weight=1,
                    dash_array="8, 8",
                    tooltip=f"48h Delivery SLA Zone (500 km) - {f.facility_name}",
                ).add_to(fmap)

    # 6. Plot Greenfield Weiszfeld Centroid if provided
    if greenfield_centroid is not None:
        c_lat = greenfield_centroid.optimal_latitude
        c_lon = greenfield_centroid.optimal_longitude
        centroid_popup = (
            f"<b>Greenfield Center of Gravity (Weiszfeld)</b><br>"
            f"<b>Optimal Coordinates:</b> {c_lat:.4f}, {c_lon:.4f}<br>"
            f"<b>Nearest Market:</b> {greenfield_centroid.nearest_region_name} "
            f"({greenfield_centroid.distance_to_nearest_km:.1f} km)<br>"
            f"<b>Weighted Avg Distance:</b> {greenfield_centroid.weighted_average_distance_km:.1f} km"
        )
        folium.Marker(
            location=[c_lat, c_lon],
            popup=folium.Popup(centroid_popup, max_width=260),
            tooltip=f"Greenfield Centroid: ({c_lat:.3f}, {c_lon:.3f})",
            icon=folium.Icon(color="purple", icon="bullseye", prefix="fa"),
        ).add_to(fmap)

    return fmap


def plot_cost_breakdown_pie(breakdown: CurrencyConvertedBreakdown) -> go.Figure:
    """Generate interactive donut chart displaying landed cost components."""
    labels = [
        "Fixed Facility Overhead",
        "Variable Handling",
        "Inbound Freight",
        "Outbound Distribution",
    ]
    values = [
        breakdown.fixed_facility_cost,
        breakdown.variable_handling_cost,
        breakdown.inbound_freight_cost,
        breakdown.outbound_freight_cost,
    ]
    colors = ["#2b5c8f", "#41b6c4", "#7fbc41", "#f781bf"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Amount: "
                + breakdown.symbol
                + " %{value:,.2f}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=f"Total Landed Cost Decomposition ({breakdown.currency})",
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )
    return fig


def plot_facility_utilization(facilities: List[FacilityStatus]) -> go.Figure:
    """Generate horizontal bar chart displaying capacity utilization across all candidate DCs."""
    fac_names = [f.facility_name for f in facilities]
    throughputs = [f.assigned_throughput for f in facilities]
    capacities = [f.max_capacity for f in facilities]
    pcts = [f.utilization_rate * 100.0 for f in facilities]
    bar_colors = ["#2ca02c" if f.is_open else "#b0b0b0" for f in facilities]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=fac_names,
            x=throughputs,
            name="Assigned Throughput",
            orientation="h",
            marker=dict(color=bar_colors),
            text=[f"{p:.1f}%" if t > 0 else "Closed" for p, t in zip(pcts, throughputs)],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Throughput: %{x:,.0f} units<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            y=fac_names,
            x=capacities,
            name="Maximum Capacity",
            mode="markers",
            marker=dict(color="#d95f02", size=12, symbol="line-ns-open", line=dict(width=3)),
            hovertemplate="<b>%{y}</b><br>Capacity Ceiling: %{x:,.0f} units<extra></extra>",
        )
    )
    fig.update_layout(
        title="Distribution Center Capacity Utilization",
        xaxis_title="Monthly Volume (Units)",
        yaxis=dict(autorange="reversed"),
        margin=dict(t=40, b=30, l=100, r=30),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )
    return fig


def plot_scenario_comparison(
    scenario_names: List[str],
    total_costs: List[float],
    lead_times: List[float],
    currency_symbol: str = "DZD",
) -> go.Figure:
    """Generate dual-axis chart comparing sensitivity scenarios on total cost and lead times."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=scenario_names,
            y=total_costs,
            name="Total Landed Cost",
            marker=dict(color="#2b5c8f"),
            hovertemplate="Cost: " + currency_symbol + " %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=scenario_names,
            y=lead_times,
            name="Weighted Average Lead Time",
            mode="lines+markers",
            marker=dict(color="#e41a1c", size=9),
            line=dict(width=3),
            hovertemplate="Avg Lead Time: %{y:.2f} days<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Scenario Sensitivity Analysis Comparison",
        margin=dict(t=40, b=30, l=30, r=30),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )
    fig.update_yaxes(title_text=f"Total Landed Cost ({currency_symbol})", secondary_y=False)
    fig.update_yaxes(title_text="Transit Duration (Days)", secondary_y=True)

    return fig
