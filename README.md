# RouteZone: Supply Chain Network Optimizer (SCNO)

Strategic two-echelon facility location, total landed cost minimization, and supply chain network resilience platform powered by Google OR-Tools and Streamlit.

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Optimization Engine](https://img.shields.io/badge/Solver-Google%20OR--Tools-orange.svg)](https://developers.google.com/optimization)
[![UI Framework](https://img.shields.io/badge/Frontend-Streamlit-red.svg)](https://streamlit.io/)
[![Test Suite](https://img.shields.io/badge/Tests-25%20Passing-brightgreen.svg)](tests/)
[![Code Standard](https://img.shields.io/badge/Standard-Google%20%26%20Apple%20Engineering-black.svg)](CONTRIBUTING.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 1. Executive Summary

RouteZone is a strategic decision-support platform designed to solve the two-echelon Capacitated Facility Location Problem (CFLP) with deterministic mixed-integer linear programming (MILP).

While tactical dispatch tools optimize vehicle routes on a daily basis (Vehicle Routing Problem), RouteZone addresses the multi-million dollar capital expenditure decisions that dictate enterprise supply chain performance over multi-year horizons:
- **Facility Portfolio Selection**: Determines the optimal subset of candidate distribution centers to lease or activate versus mothball.
- **Upstream Inbound Drayage**: Establishes replenishment flows connecting gateway ports and manufacturing hubs to regional distribution centers.
- **Downstream Allocation**: Allocates regional customer markets to open warehouses under strict single-sourcing constraints.
- **Total Landed Cost Minimization**: Balances fixed warehouse overhead, handling fees, inbound transport, and outbound distribution tariffs.
- **Risk and Resilience Quantification**: Stress-tests operational continuity against catastrophic single-node outages (N-1 failure simulation).

```
                      TWO-ECHELON SUPPLY CHAIN TOPOLOGY

 [ Supply Gateways ]             [ Distribution Centers ]            [ Demand Markets ]
  (Ports / Plants)                 (Candidate Warehouses)           (Regional Customers)

   +-------------+                  +------------------+              +---------------+
   | Port Algiers| === Inbound ===> | DC Algiers (F1)  | === Outbound | Algiers City  |
   +-------------+     Freight      +------------------+    Freight   +---------------+
                                      \              /
   +-------------+                     \            /                 +---------------+
   | Port Bejaia | ===================> \          / ===============> | Setif Market  |
   +-------------+                       \        /                   +---------------+
                                          \      /
                                    +------------------+              +---------------+
                                    | DC Constantine   | ===========> | Constantine   |
                                    +------------------+              +---------------+
```

---

## 2. Platform Architecture & Visual Showcase

### Step 1: Data Studio & Ingestion Workflow

#### 1. Initial Blank State & Ingestion Choice
The platform initializes in a clean blank state, allowing users to enter custom operational records, auto-fill standardized benchmark datasets, or upload enterprise CSV files.

![01 Data Studio Blank State](docs/img/01_data_studio_blank.png)

#### 2. CSV Schema Upload & Integration
Users can import four distinct operational matrices: Regional Customer Demand, Primary Supply Gateways, Candidate Distribution Centers, and custom Freight Rate/Lead Time tariffs.

![02 CSV Upload Guide](docs/img/02_csv_uploader_guide.png)

#### 3. In-Place Table Editing & Capacity Auditing
Every data record is directly editable in-place via interactive data editors. The system continuously validates capacity sanity bounds (Supply $\ge$ Demand) before enabling solver execution.

![03 Editable Data Tables](docs/img/03_editable_data_tables.png)

#### 4. Visual Workflow Pipeline & Methodology Guide
A 4-step vector workflow banner guides users through Ingestion, Capacity Audit, MILP Optimization, and Executive Decision Cockpit.

```
                            WORKFLOW PIPELINE

  [ Step 1: Ingestion ] ──> [ Step 2: Audit ] ──> [ Step 3: MILP ] ──> [ Step 4: Cockpit ]
   (Auto-fill or CSV)     (Supply vs Demand)     (Google OR-Tools)    (KPIs, Map, Risk)
```

![04 Workflow Pipeline Guide](docs/img/04_workflow_methodology_guide.png)

---

### Step 2: Executive Decision Cockpit & Analytics

#### 5. Executive Metric Cards & Status Quo Comparison
Immediate C-suite visibility over Total Landed Cost, Net Financial Savings vs Baseline, Number of Active Warehouses, Weighted Average Lead Time, Unit Landed Cost, and Scope 3 Carbon Emissions.

![05 Cockpit Executive KPIs](docs/img/05_cockpit_executive_kpis.png)

#### 6. Interactive Network Cartography, SLA Radii & Greenfield Centroid
OpenStreetMap geospatial visualization displaying supply gateways (blue diamonds), open distribution hubs (green markers), closed facilities (gray markers), demand markets (orange circles scaled to volume), inbound drayage polylines, outbound distribution routes, dual-band SLA service radii (24h at 250 km, 48h at 500 km), and the Greenfield Weiszfeld optimal demand-weighted centroid (red target marker).

![06 Interactive Network Map](docs/img/06_network_map_routing.png)

#### 7. Total Landed Cost Decomposition & Working Capital Centralization
Interactive Plotly cost decomposition breakdown (fixed facility overhead, handling fees, primary inbound freight, outbound distribution) accompanied by Eppen-Maister Square Root Law safety stock holding evaluation.

![07 Landed Cost Breakdown](docs/img/07_landed_cost_breakdown.png)

#### 8. Facility Throughput Capacity & Utilization Rates
Direct analysis of open vs closed candidate warehouses, showing throughput utilization percentages, allocated monthly volume, and residual capacity headroom.

![08 Facility Capacity Utilization](docs/img/08_facility_utilization.png)

#### 9. Customer Market Single-Sourcing Allocation
Tabular audit of every regional customer market, assigned serving distribution center, volume delivered, integer transit days, unit freight tariffs, and total outbound transport expenditure.

![09 Customer Market Allocation](docs/img/09_customer_market_allocation.png)

#### 10. Upstream Port Replenishment Inflow
Full traceability of primary inbound freight flows moving from seaports to active distribution hubs with tonnage volumes and unit transport economics.

![10 Upstream Inflow Allocations](docs/img/10_upstream_inflow.png)

#### 11. Automated What-If Sensitivity Scenarios
Side-by-side scenario modeling comparing the baseline network against High Fuel (+30% freight index), Peak Demand (+20% volume), Facility Overhead Surge (+25% fixed costs), and Combined Stress scenarios.

![11 Sensitivity Scenarios](docs/img/11_whatif_sensitivity_scenarios.png)

#### 12. N-1 Supply Chain Crisis Resilience & Stress-Testing
Simulates catastrophic node blackouts (port closure or warehouse fire). Calculates the Network Resilience Score (0 to 100), financial cost surge, delivery delay spikes, emergency rerouted customer markets, and Single Point of Failure (SPOF) root-cause diagnostic breakdown.

![12 N-1 Crisis Resilience Simulator](docs/img/12_n1_crisis_resilience.png)

#### 13. Corporate Multi-Tab Audit Workbook Export
One-click generation of a multi-tab corporate Excel audit workbook formatted with openpyxl in the active reporting currency (DZD, USD, EUR).

![13 Excel Audit Export](docs/img/13_excel_audit_export.png)

---

## 3. Core Enterprise Capabilities

### 1. Mixed-Integer Linear Program (MILP)
Solves the two-echelon CFLP formulation via Google OR-Tools. Enforces single-sourcing, warehouse throughput capacities, port output quotas, flow conservation, and optional delivery service level agreement (SLA) transit day ceilings.

### 2. Geodesic Transport and Road Circuity Engine
Computes geodesic distances between all supply nodes, candidate warehouses, and customer regions using the Haversine formula. Automatically applies a 1.25 road circuity factor to account for commercial highway geography, converting distances into transit day estimates based on professional driving limits (8 hours/day at 60 km/h).

### 3. Dual-Band SLA Delivery Coverage Radii
Renders visual service coverage zones around each active distribution hub:
- **Green Translucent Zone (250 km)**: Guaranteed 24-hour delivery perimeter.
- **Amber Translucent Zone (500 km)**: Standard 48-hour delivery perimeter.
- **Uncovered Pockets**: Identifies remote customer markets requiring 3 or more transit days.

![Cartographic Guidance](docs/img/cartographic_guide.png)

### 4. Greenfield Continuous Center of Gravity (Weiszfeld Algorithm)
Calculates the theoretical demand-weighted geographic centroid using the Weiszfeld continuous optimization algorithm. Displays the target balance point as a red target marker on the interactive map, providing a baseline to evaluate the spatial quality of candidate warehouse leases.

### 5. Scope 3 Carbon Footprint Accounting
Quantifies greenhouse gas (GHG) freight emissions in metric tonnes of CO2 using the ADEME and European Environment Agency heavy truck standard (0.070 kg CO2 per ton-kilometer). Evaluates environmental impact relative to a single-warehouse status quo baseline.

### 6. Working Capital & Safety Stock Centralization
Applies the Eppen-Maister Square Root Law of Inventory:

$$\text{Safety Stock}(N) = \text{Safety Stock}(1) \times \sqrt{N}$$

Demonstrates the trade-off between inventory holding capital (at an 18% annual carrying rate) and decentralized transportation savings when expanding from 1 to N facilities.

### 7. N-1 Supply Chain Crisis & Disruption Contingency Simulator
Stress-tests the network by disabling an active gateway port or distribution center. Re-solves the degraded contingency network in real time to compute:
- **Network Resilience Score (0 to 100)**: Quantitative measure of absorption capacity.
- **Financial Cost Surge**: Budgetary increase resulting from emergency detour miles.
- **Lead Time Delta**: Customer delivery delay impact.
- **Single Point of Failure (SPOF) Detection**: Identifies bottlenecks where surviving capacity cannot satisfy aggregate demand, outputting executive mitigation steps.

### 8. Multi-Currency Normalization
Solves the linear optimization program in base Algerian Dinar (DZD) to guarantee mathematical linearity, converting outputs into USD or EUR using configurable foreign exchange conversion rates.

![Operational Sensitivity Controls](docs/img/parameter_guide.png)

---

## 4. Mathematical Formulation

The optimization engine minimizes total landed distribution cost:

### Decision Variables
- $y_i \in \{0, 1\}$: Binary decision variable indicating whether candidate distribution center $i$ is activated.
- $x_{i, j} \in \{0, 1\}$: Binary variable indicating whether customer market $j$ is allocated to facility $i$.
- $flow\_in_{s, i} \ge 0$: Continuous volume shipped from supply gateway $s$ to distribution center $i$.

### Objective Function
$$\min \sum_{i \in F} f_i \cdot y_i + \sum_{i \in F} \sum_{j \in R} v_i \cdot d_j \cdot x_{i, j} + \sum_{s \in S} \sum_{i \in F} c^{in}_{s, i} \cdot flow\_in_{s, i} + \sum_{i \in F} \sum_{j \in R} c^{out}_{i, j} \cdot d_j \cdot x_{i, j}$$

Where:
- $f_i$: Monthly fixed lease and operational overhead of facility $i$.
- $v_i$: Variable handling cost per unit at facility $i$.
- $d_j$: Monthly demand of customer region $j$.
- $c^{in}_{s, i}$: Inbound freight cost per unit from gateway $s$ to facility $i$.
- $c^{out}_{i, j}$: Outbound freight cost per unit from facility $i$ to region $j$.

### Mathematical Constraints
1. **Single-Sourcing**: Every customer market is served by exactly one distribution center:
   $$\sum_{i \in F} x_{i, j} = 1 \quad \forall j \in R$$

2. **Facility Capacity Ceiling**: Demand allocated to an active facility cannot exceed its throughput limit:
   $$\sum_{j \in R} d_j \cdot x_{i, j} \le C^{fac}_i \cdot y_i \quad \forall i \in F$$

3. **Allocation-Activation Linking**: Customer assignment requires prior facility activation:
   $$x_{i, j} \le y_i \quad \forall i \in F, \; j \in R$$

4. **Flow Conservation**: Inbound replenishment volume equals outbound regional shipments:
   $$\sum_{s \in S} flow\_in_{s, i} = \sum_{j \in R} d_j \cdot x_{i, j} \quad \forall i \in F$$

5. **Supply Gateway Capacity**: Total shipments from a gateway cannot exceed its physical capacity:
   $$\sum_{i \in F} flow\_in_{s, i} \le C^{sup}_s \quad \forall s \in S$$

6. **Delivery SLA Threshold (Optional)**: Maximum allowable transit days cannot exceed contract limit $L^{max}$:
   $$lead\_time_{i, j} \cdot x_{i, j} \le L^{max} \quad \forall i \in F, \; j \in R$$

---

## 5. Repository Structure

```
RouteZone/
├── app.py                     # Streamlit enterprise decision cockpit
├── config.py                  # Operational defaults, speeds, circuity, FX rates
├── requirements.txt           # Pinned production dependencies
├── CONTRIBUTING.md            # Open source contribution and engineering standards
├── data/
│   ├── example_algeria.csv    # Benchmark demand dataset (12 Algerian wilayas)
│   ├── suppliers_example.csv  # Gateway ports (Port of Algiers, Port of Bejaia)
│   ├── facilities_example.csv # Candidate DC options (Algiers, Oran, Constantine, Annaba)
│   └── README.md              # Data dictionary and schema specifications
├── docs/
│   └── img/                   # Visual artifacts and platform screenshots
├── src/
│   ├── __init__.py
│   ├── geo_engine.py          # Geodesic Haversine calculations and transit day model
│   ├── data_loader.py         # Pydantic schema validation and matrix synthesis
│   ├── optimizer.py           # Google OR-Tools two-echelon MILP solver
│   ├── network_analyzer.py    # Multi-currency engine and baseline status quo auditor
│   ├── carbon_engine.py       # Scope 3 GHG freight emissions accounting
│   ├── inventory_engine.py    # Eppen-Maister Square Root Law and working capital engine
│   ├── greenfield_engine.py   # Weiszfeld continuous center-of-gravity algorithm
│   ├── resilience_engine.py   # N-1 disruption simulation and SPOF diagnostic engine
│   ├── visualization.py       # Folium cartographic maps and Plotly analytics
│   └── report_generator.py    # 5-tab corporate Excel audit workbook generator
└── tests/
    ├── test_carbon_engine.py
    ├── test_data_loader.py
    ├── test_geo_engine.py
    ├── test_greenfield_engine.py
    ├── test_inventory_engine.py
    ├── test_network_analyzer.py
    ├── test_optimizer.py
    ├── test_report_generator.py
    └── test_resilience_engine.py
```

---

## 6. Installation & Execution

### System Requirements
- Python 3.10 or higher (Tested and certified on Python 3.12 and 3.14).
- Operating System: Linux, macOS, or Windows.

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sambovix/routezone.git
   cd routezone
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Launch the application**:
   ```bash
   streamlit run app.py
   ```
   Access the dashboard at `http://localhost:8501` (or the port displayed in your terminal).

---

## 7. Verification and Testing

Execute the automated test suite covering all mathematical formulations, data loaders, and analytical engines:

```bash
pytest tests/ -v
```

Expected output:
```text
============================= test session starts =============================
collected 25 items

tests/test_carbon_engine.py::test_calculate_transport_emissions PASSED   [  4%]
tests/test_carbon_engine.py::test_calculate_transport_emissions_invalid_inputs PASSED [  8%]
tests/test_data_loader.py::test_load_regions_valid PASSED                [ 12%]
tests/test_data_loader.py::test_load_regions_missing_column PASSED       [ 16%]
tests/test_data_loader.py::test_load_regions_invalid_latitude PASSED     [ 20%]
tests/test_data_loader.py::test_synthesize_matrices PASSED               [ 24%]
tests/test_geo_engine.py::test_haversine_distance_known_coordinates PASSED [ 28%]
tests/test_geo_engine.py::test_haversine_same_point_is_zero PASSED       [ 32%]
tests/test_geo_engine.py::test_road_distance_applies_circuity PASSED     [ 36%]
tests/test_geo_engine.py::test_estimate_lead_time_days PASSED            [ 40%]
tests/test_geo_engine.py::test_estimate_lead_time_invalid_capacity PASSED [ 44%]
tests/test_greenfield_engine.py::test_weiszfeld_symmetric_points PASSED  [ 48%]
tests/test_greenfield_engine.py::test_weiszfeld_algeria_data PASSED      [ 52%]
tests/test_greenfield_engine.py::test_weiszfeld_empty_raises PASSED      [ 56%]
tests/test_inventory_engine.py::test_square_root_law_scaling PASSED      [ 60%]
tests/test_inventory_engine.py::test_zero_facilities PASSED              [ 64%]
tests/test_network_analyzer.py::test_convert_costs_to_usd PASSED         [ 68%]
tests/test_network_analyzer.py::test_compare_with_baseline PASSED        [ 72%]
tests/test_optimizer.py::test_optimizer_solves_optimally PASSED          [ 76%]
tests/test_optimizer.py::test_optimizer_respects_max_lead_time PASSED    [ 80%]
tests/test_optimizer.py::test_optimizer_detects_infeasible_capacity PASSED [ 84%]
tests/test_report_generator.py::test_generate_excel_report PASSED        [ 88%]
tests/test_resilience_engine.py::test_simulate_supplier_disruption PASSED [ 92%]
tests/test_resilience_engine.py::test_simulate_facility_disruption PASSED [ 96%]
tests/test_resilience_engine.py::test_invalid_node_raises PASSED         [100%]

======================= 25 passed in 0.85s ========================
```

---

## 8. Author Profile

**Mohamed AYATI**
- Master Student in Supply Chain Management with a strong focus on software engineering, IT architectures, Artificial Intelligence, digitalization, and operations research problem solving.
- Personal Website: [devaultos.me](https://devaultos.me)
- GitHub Profile: [@sambovix](https://github.com/sambovix)
- Repository: [sambovix/routezone](https://github.com/sambovix/routezone)

---

## 9. Collaboration & Contributing

Contributions from the open-source community, operations researchers, and supply chain practitioners are encouraged. Please consult [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on coding hygiene, Google-style docstrings, type annotations, and pull request procedures.

---

## 10. License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
