# Contributing to RouteZone

Contributions from developers, supply chain researchers, and operations research specialists are welcome. To maintain high code quality and mathematical reliability, all contributors must follow the guidelines outlined below.

---

## 1. Code of Conduct and Professional Standards

RouteZone follows open source engineering standards inspired by the Google Python Style Guide and Apple software engineering practices:
- Deterministic, maintainable, and mathematically sound implementations.
- Professional, respectful, and technical collaboration across issue discussions and pull requests.
- Zero boilerplate filler: communications should focus on operational metrics, algorithm complexity, and test coverage.

---

## 2. Getting Started

### Prerequisites
- Python 3.10 or higher (Python 3.12+ recommended).
- Git version control.

### Local Development Setup

1. Fork the repository on GitHub and clone your fork locally:
   ```bash
   git clone https://github.com/sambovix/routezone.git
   cd routezone
   ```

2. Create and activate an isolated virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install production and testing dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Verify your environment by executing the automated test suite:
   ```bash
   pytest tests/ -v
   ```

---

## 3. Development Workflow

1. Create a descriptive feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
   or for bug fixes:
   ```bash
   git checkout -b fix/issue-description
   ```

2. Make modular, focused changes that solve a single problem.

3. Verify syntax and static analysis before committing:
   ```bash
   python -m py_compile app.py
   pytest tests/ -v
   ```

---

## 4. Code Hygiene and Engineering Standards

### Type Annotations and Static Typing
All functional code in `src/` must include explicit standard Python type hints (compatible with `mypy`):
```python
def calculate_lead_time(
    distance_km: float,
    average_speed_kmh: float,
    daily_driving_hours: float,
) -> int:
    ...
```

### Docstrings and Comments
- Use Google-style docstrings for all public modules, classes, and functions:
  ```python
  """Compute geodesic road distance using Haversine formulation.

  Args:
      lat1: Origin latitude in degrees.
      lon1: Origin longitude in degrees.
      lat2: Destination latitude in degrees.
      lon2: Destination longitude in degrees.
      circuity_factor: Road terrain multiplier.

  Returns:
      Estimated road distance in kilometers.

  Raises:
      ValueError: If coordinates fall outside valid geographic ranges.
  """
  ```
- Avoid syntax-explaining comments. Comments are reserved for non-obvious mathematical formulations, business logic constraints, and algorithmic trade-offs.

### Mathematical Rigor
- Solver formulations must preserve linearity whenever possible to ensure fast convergence.
- Always include defensive input checks for negative demand, zero capacity, and division-by-zero bounds before solver execution.

---

## 5. Testing Requirements

- Every new engine, module, or algorithm extension must be accompanied by comprehensive unit tests in the `tests/` directory.
- Test suites must verify:
  - Nominal execution cases with known baseline outputs.
  - Edge cases (such as zero volume, symmetric coordinates, and extreme capacity thresholds).
  - Explicit exception handling for invalid inputs.
- All tests must pass with zero failures before opening a pull request:
  ```bash
  pytest tests/ -v
  ```

---

## 6. Commit Message Standards

RouteZone adheres to Conventional Commits:
- `feat:` A new operational feature or analytical engine.
- `fix:` A bug fix or mathematical constraint correction.
- `docs:` Documentation or README updates.
- `perf:` Performance improvements in solver execution or data synthesis.
- `test:` Adding or updating unit tests.
- `refactor:` Code restructuring without altering external functionality.

Rules:
- Write messages in the imperative mood (for example, `feat: add carbon accounting engine`, not `feat: added carbon accounting engine`).
- Keep commit titles under 72 characters.
- Do not use emojis in commit messages or code comments.

---

## 7. Pull Request Process

1. Push your branch to your GitHub fork:
   ```bash
   git push origin feat/your-feature-name
   ```
2. Open a Pull Request against the `main` branch of `sambovix/routezone`.
3. Provide a clear description including:
   - Summary of mathematical or operational changes.
   - Test results and performance benchmarks.
   - Any modifications to data schemas or user interface components.
4. Maintainers will review the code for mathematical validity, style compliance, and performance impact prior to merging.
