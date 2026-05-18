# CLAUDE.md — opencot

This file gives you full context on the project. Read it before touching anything.

---

## What is opencot?

`opencot` is a Python library for fetching and working with CFTC Commitment of Traders (COT) data. Think of it as the `yfinance` of COT data — clean, Pythonic, one-liner access to a public but annoying-to-use data source.

The CFTC publishes COT reports every Friday at 3:30pm ET, reflecting positioning data as of the prior Tuesday. The data is public, requires no authentication, and is available back to 1986. The problem is the access layer is terrible — ZIP files, inconsistent column names, no instrument lookup. That's what opencot solves.

---

## Vision & Philosophy

**This is an API wrapper, not a utility kit.** The goal is clean data access, not a toolbox of helpers. The user should be able to get meaningful COT data in one line without knowing anything about how the CFTC structures its files.

The north star API:

```python
import opencot as cot

df = cot.get("Gold", report="disaggregated", years=5)
df["net_managed_money"]   # already computed
df["cot_index"]           # positioning vs historical range, 0–100
```

Design decisions, in order of priority:
1. **Simplicity** — the API should feel obvious to a quant who has never read the docs
2. **Correctness** — data integrity over features; wrong data is worse than missing features
3. **Performance** — cache aggressively so repeated calls are instant
4. **Coverage** — all 4 report types, full history

---

## Decisions Already Made

| Decision | Choice | Reason |
|---|---|---|
| License | MIT | Maximum adoption, no institutional friction |
| Package manager | uv | Modern standard, clean pyproject.toml |
| PyPI name | `opencot` | Available, clean, signals open data access |
| GitHub repo | `opencot` | Matches PyPI name exactly |
| Python import | `import opencot as cot` | Short alias reads naturally in analysis code |
| Min Python version | 3.10+ | Modern, widely supported |
| Core dependencies | pandas, requests | Keep it lean |

---

## Data Source

All data comes from the CFTC directly. No third-party APIs, no scraping, no authentication required.

### Primary: ZIP file downloads

- **Download base URL:** `https://www.cftc.gov/files/dea/history/`
- **File naming:** `{report}_{variant}_txt_{year}.zip` — e.g. `fut_disagg_txt_2024.zip`
- **Format:** CSV (comma-delimited text) inside ZIP archives
- **Variants:** `fut` = futures only, `com` = combined (futures + options)
- **Report type prefixes in filenames:**

| Report | File prefix | Example |
|---|---|---|
| Legacy | `deahistfo` / `deacot` | `deahistfo{year}.zip` |
| Supplemental | `fut_cit_txt` | `fut_cit_txt_{year}.zip` |
| Disaggregated | `fut_disagg_txt` / `com_disagg_txt` | `fut_disagg_txt_{year}.zip` |
| TFF | `fut_fin_txt` / `com_fin_txt` | `fut_fin_txt_{year}.zip` |

The CFTC has 4 report types:

| Report | Key | Coverage | Available From |
|---|---|---|---|
| Legacy | `legacy` | Physical + financial contracts | 1986 |
| Supplemental | `supplemental` | Selected agricultural (CIT) | 2006 |
| Disaggregated | `disaggregated` | Physical commodities only | Sep 2009 |
| Traders in Financial Futures | `tff` | Financial contracts only | Jul 2010 |

Each report comes in `futures_only` and `futures_and_options` variants.

### Secondary: Socrata SODA API

The CFTC also exposes all COT data via a REST API at `publicreporting.cftc.gov` (Socrata platform). This is **not used as primary** because:
- Optional app token required to avoid IP throttling (adds registration friction)
- 50,000 record limit per request requires pagination for full history
- ZIP files are simpler to cache deterministically by year

The Socrata API is worth revisiting if we ever need real-time intraweek updates or server-side filtering. Key dataset IDs: Legacy Futures Only `6dca-aqww`, Disaggregated Futures Only `72hh-3qpy`, TFF Futures Only `gpe5-46if`.

---

## Known Pain Points to Solve

These are the specific failures of the existing `cot-reports` library that opencot must fix:

1. **No instrument lookup** — you currently need to know the exact CFTC market name string. opencot should support human-readable names and fuzzy matching (`"Gold"`, `"Crude"`, `"EUR"`)
2. **No caching** — every call re-downloads multi-MB ZIP files. opencot should cache locally with configurable TTL
3. **No derived metrics** — raw data only, no net positioning, no COT index, no % of open interest
4. **Clunky multi-year fetching** — users have to write their own loops. opencot should handle date ranges natively
5. **Fragile column names** — CFTC column names are inconsistent across report types. opencot should normalize to clean, snake_case names

---

## Derived Metrics to Include

These are the metrics practitioners actually use. Build them in as computed columns:

- `net_[trader_class]` — long minus short for each trader classification
- `net_[trader_class]_pct_oi` — net position as % of total open interest
- `cot_index` — where current net positioning sits vs its N-period range, scaled 0–100 (like RSI but for positioning). Default N=3 years
- `change_[trader_class]` — week-over-week change in net positioning

---

## Project Structure

```
opencot/
├── CLAUDE.md               # this file
├── README.md
├── pyproject.toml
├── src/
│   └── opencot/
│       ├── __init__.py     # public API surface
│       ├── fetch.py        # CFTC data fetching + caching
│       ├── parse.py        # ZIP/CSV parsing + column normalization
│       ├── instruments.py  # instrument name → CFTC market code lookup
│       ├── metrics.py      # derived metrics (net positioning, COT index, etc.)
│       └── types.py        # enums and type aliases
├── tests/
│   ├── test_fetch.py
│   ├── test_parse.py
│   └── test_metrics.py
└── examples/
    └── basic_usage.ipynb
```

---

## Public API Surface

Keep the public API minimal. Everything in `__init__.py` should be intentional.

```python
# Primary interface
cot.get(instrument, report="disaggregated", variant="futures_only", years=3)

# List available instruments
cot.instruments(report="disaggregated")

# Clear local cache
cot.clear_cache()

# Low-level access if needed
cot.fetch_raw(report="legacy", year=2023)
```

---

## Style & Code Conventions

- Snake_case everywhere
- Type hints on all public functions
- Docstrings on all public functions (NumPy style)
- Ruff for linting and formatting
- pytest for tests
- No classes in the public API unless genuinely necessary — functions first

---

## What "Done Well" Looks Like

A quant who has never heard of opencot should be able to:
1. `pip install opencot`
2. Read the README for 2 minutes
3. Have a clean DataFrame with net positioning for Gold futures covering 5 years

That's the bar. If that flow has any friction, the library isn't done.
