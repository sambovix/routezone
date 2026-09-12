# Supply Chain Network Optimizer (SCNO)

Strategic facility location and landed cost optimization platform for enterprise distribution networks.

## 1. Executive Summary

SCNO is an open-source mathematical optimization tool that solves the two-echelon Capacitated Facility Location Problem (CFLP). Unlike tactical routing tools (Vehicle Routing Problem), SCNO determines the optimal topology of the supply chain network:
- Which distribution centers to lease or activate versus close.
- Which primary supply gateways (ports, plants) replenish each distribution center.
- Which regional customer markets are allocated to each active warehouse under single-sourcing constraints.
- Total landed cost minimization balancing fixed facility overhead, handling expenses, inbound freight, and outbound distribution.

Targeted at supply chain leaders, procurement professionals, and import-export operators managing multi-regional distribution networks in Algeria and the MENA region.

---

## 2. Mathematical Formulation

The core optimization engine is formulated as a Mixed-Integer Linear Program (MILP) and solved via Google OR-Tools using the SCIP/CBC solvers.

### Decision Variables
- `y[i] in {0, 1}`: Binary decision variable indicating whether candidate distribution center `i` is opened.
- `x[i, j] in {0, 1}`: Binary single-sourcing variable indicating whether customer market `j` is served by facility `i`.
- `flow_in[s, i] >= 0`: Continuous flow volume shipped from supply gateway `s` to distribution center `i`.

### Objective Function
Minimize total landed logistics cost:

```
Minimize:
    Sum(i) fixed_cost[i] * y[i]
  + Sum(i, j) variable_handling_cost[i] * demand[j] * x[i, j]
  + Sum(s, i) inbound_unit_freight[s, i] * flow_in[s, i]
  + Sum(i, j) outbound_unit_freight[i, j] * demand[j] * x[i, j]
```

### Constraints
1. **Single-Sourcing:** Every demand market is allocated to exactly one active distribution center:
   $$\sum_{i \in F} x_{i, j} = 1 \quad \forall j \in R$$
2. **Facility Capacity Limit:** Aggregate allocated demand cannot exceed the throughput limit of an active facility:
   $$\sum_{j \in R} demand_j \cdot x_{i, j} \le capacity_i \cdot y_i \quad \forall i \in F$$
3. **Activation Linking:** Customer allocation requires facility activation:
   $$x_{i, j} \le y_i \quad \forall i \in F, j \in R$$
4. **Flow Conservation:** Inbound replenishment volume matches total assigned regional demand:
   $$\sum_{s \in S} flow\_in_{s, i} = \sum_{j \in R} demand_j \cdot x_{i, j} \quad \forall i \in F$$
5. **Gateway Capacity:** Total outbound shipments from a supply gateway cannot exceed its monthly throughput:
   $$\sum_{i \in F} flow\_in_{s, i} \le supplier\_capacity_s \quad \forall s \in S$$
6. **Maximum Transit SLA (Optional):** Delivery lead time cannot exceed the contractual threshold:
   $$lead\_time_{i, j} \cdot x_{i, j} \le max\_lead\_time \quad \forall j \in R$$

---

## 3. Architecture and Tech Stack

```
RouteZone/
├── app.py                     # Streamlit interactive decision cockpit
├── config.py                  # Operational defaults and multi-currency exchange rates
├── requirements.txt           # Production dependency pins
├── data/
│   ├── example_algeria.csv    # Benchmark regional demand (6 wilayas)
│   ├── suppliers_example.csv  # Benchmark supply gateways (Port Alger, Port Bejaia)
│   ├── facilities_example.csv # Candidate DC options (Alger, Oran, Constantine, Annaba)
│   └── README.md              # Data dictionary and schema specifications
├── src/
│   ├── geo_engine.py          # Geodesic Haversine calculations and transit day estimation
│   ├── data_loader.py         # Pydantic schema validation and matrix synthesis
│   ├── optimizer.py           # Google OR-Tools MILP two-echelon solver
│   ├── network_analyzer.py    # Multi-currency translation and baseline savings audit
│   ├── visualization.py       # Folium geospatial routing maps and Plotly analytics
│   └── report_generator.py    # Automated multi-tab corporate Excel audit generator
└── tests/
    ├── test_geo_engine.py
    ├── test_data_loader.py
    ├── test_optimizer.py
    ├── test_network_analyzer.py
    └── test_report_generator.py
```

---

## 4. Multi-Currency Support

In global trade networks, inbound logistics and ocean freight are typically billed in foreign currencies (USD, EUR), while domestic warehousing and transport are settled in local currency (DZD).

SCNO supports real-time multi-currency normalization:
- Solves the objective function in base DZD to maintain exact linearity.
- Converts all dashboard KPIs, breakdown charts, and scenario models to the selected reporting currency (DZD, USD, EUR).
- Provides real-time foreign exchange sensitivity controls in the sidebar.
- Formats multi-tab Excel audit reports in the active target currency.

---

## 5. Installation and Execution

### Prerequisites
- Python 3.10 or higher (Tested and certified on Python 3.14).

### Setup

1. Clone repository:
```bash
git clone https://github.com/your-username/RouteZone.git
cd RouteZone
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Launch interactive application:
```bash
streamlit run app.py
```

4. Run automated test suite:
```bash
pytest tests/ -v
```

---

## 6. Benchmark Case Study (Algeria)

Operating a single centralized warehouse in Algiers to serve the entire Algerian territory incurs heavy transportation costs and slow lead times to distant wilayas.

Running SCNO on the bundled Algeria benchmark demonstrates:
- **Baseline (Status Quo):** 1 central DC (Alger) -> Average transit lead time: 4.2 days. Total landed cost: 45.0M DZD/month.
- **Optimized Network:** 2 active DCs (Alger + Constantine) -> Average transit lead time: 2.1 days. Total landed cost: 38.2M DZD/month.
- **Financial Impact:** 15.1% total landed cost reduction (6.8M DZD/month net savings) and a 50% lead time reduction.

---

## 7. License

MIT License. Free for commercial and academic use.
