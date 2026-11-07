# Power BI build guide

This guide rebuilds the report from the CSVs in `data/clean`. It takes about 45 minutes in Power BI Desktop (free).

## 1. Load the data

You can load the data in either of two ways:

- **From GitHub (keeps the report refreshable):** use the queries in [`load_from_github.pq`](load_from_github.pq).
- **From a local clone:** use Get data → Text/CSV for each file in `data/clean`.

Then apply the theme: View → Themes → Browse for themes → [`theme_scotland_ev.json`](theme_scotland_ev.json).

## 2. Model (star schema)

Create `dim_year` with Modeling → New table:

```DAX
dim_year = DATATABLE ( "year", INTEGER, { {2020}, {2021}, {2022}, {2023}, {2024}, {2025}, {2026} } )
```

Set up these relationships. Every one is single-direction, one-to-many, running from the dimension to the fact.

| From (one) | To (many) | Key |
|---|---|---|
| `dim_council` | `fact_taxi_fleet` | `ons_code` |
| `dim_council` | `fact_ev_taxi_funding_by_council` | `ons_code` |
| `dim_council` | `fact_loan_counts_2022_23` | `ons_code` |
| `dim_council` | `fact_plugin_cars` | `ons_code` |
| `dim_council` | `council_risk_indicators` | `ons_code` |
| `dim_council` | `data_quality_log` | `ons_code` |
| `dim_year` | `fact_taxi_fleet` | `year` |
| `dim_year` | `fact_plugin_cars` | `year` |

Two tables are left unrelated on purpose:

- `fact_funding_by_year` is Scotland-level and uses financial years.
- `fact_taxi_fleet_scotland` holds the published national totals.

In `fact_plugin_cars`, the Scotland row (`S92000003`) has no match in `dim_council`. Filter it out with a visual or page filter wherever you slice by council.

Finally, paste the measures from [`measures.dax`](measures.dax) into a `_Measures` table.

## 3. Pages

### Page 1 – Overview

**Question:** where did the EV taxi money go?

- **KPI cards:** `EV Taxi Funding £`, `Hackney Loans £`, `Switched On Taxis £`, `Funded Councils`, `Higher Priority Councils`.
- **Stacked column:** `fact_funding_by_year`, with financial_year on the axis and `EV Taxi Funding by Year £` as the value, broken down by stream.
- **Filled map (shape map):** `dim_council[council]` coloured by `EV Taxi Funding £`. Use Scotland council boundaries from the ONS Open Geography Portal, converted to TopoJSON.
- **Text box:** `Headline Text`.

### Page 2 – Fleet vs funding

**Question:** did funded areas keep their licensed fleets?

- **Line chart:** `dim_year[year]` with `Taxis` and `Private Hire Cars`. Add a council slicer.
- **Bar chart:** councils sorted by `Funding per Licensed Vehicle £`. Use conditional formatting with **Field value → Exposure Colour**.
- **Scatter:**
  - X axis: `Funding per Licensed Vehicle £` (log scale)
  - Y axis: `Fleet Change %`
  - Details: council
  - Legend: `audit_priority_tier`
- **Table:** council, year, taxis, PHC, total, quality_flag. Turn on conditional icons for `is_reliable`.

### Page 3 – Where funded EVs end up

**Question:** is private EV ownership growing faster where taxi funding was heavy?

- **Line chart:** `BEV Cars Private (year end)` and `BEV Cars Company (year end)` by year.
- **Scatter:** `EV Taxi Funding £` against `Private BEV Growth % (2021–2025)` by council.
- **Note card:** "Renfrewshire and Stirling hold leasing-company head offices; company-kept counts there are not local cars."

### Page 4 – Audit priority

**Question:** where should an auditor sample first?

- **Table:** council, `Audit Priority Rank`, `Audit Priority Score`, the three component scores, and the tier.
- **Bar chart:** decomposition of the score, with a stacked bar of the three component scores weighted 0.5/0.3/0.2.
- **Text panel:** method and limitations, copied from the README.
- **Button:** link to `docs/FOI_TEMPLATES.md` for next steps.

### Page 5 – Data quality

**Question:** can we trust the inputs?

- **Matrix:** source × check, counting `DQ Issues`.
- **Table:** `data_quality_log`, filtered to `severity = High` by default.
- **Card:** `Fleet Data Completeness %`.

## 4. Publish

Save the file as `powerbi/Scotland_EV_Taxi_Compliance.pbix` and commit it.

Publishing to the web is optional; if you do, use File → Publish → Publish to web and put the link in the README.

Before sharing, remove any vehicle-level data you have loaded locally.
