# Benchmark Datasets

This directory contains standardized benchmark datasets for the Supply Chain Network Optimizer.

## File Specifications

### 1. example_algeria.csv (Regional Demand)
- `region_id`: Unique identifier for the customer market or administrative wilaya (e.g. R1, R2).
- `region_name`: Human-readable location name.
- `latitude`: Geodetic latitude in decimal degrees.
- `longitude`: Geodetic longitude in decimal degrees.
- `demand_units_month`: Monthly aggregate demand volume in standard sales units.

### 2. suppliers_example.csv (Supply Gateways)
- `supplier_id`: Unique identifier for primary source or port terminal (e.g. S1).
- `supplier_name`: Gateway description.
- `latitude`: Geodetic latitude in decimal degrees.
- `longitude`: Geodetic longitude in decimal degrees.
- `capacity_units_month`: Maximum monthly throughput available from this source.

### 3. facilities_example.csv (Candidate Distribution Centers)
- `facility_id`: Unique facility identifier (e.g. F1).
- `facility_name`: Distribution center label.
- `latitude`: Geodetic latitude in decimal degrees.
- `longitude`: Geodetic longitude in decimal degrees.
- `fixed_cost_dzd_month`: Monthly leasing, overhead, and operating expenditure to keep the facility active.
- `variable_cost_dzd_per_unit`: Unit handling and inventory holding cost per throughput unit.
- `max_capacity_units`: Maximum physical throughput capacity per month.
- `is_existing`: Binary indicator (1 if the warehouse is currently leased, 0 if it is a greenfield candidate).
