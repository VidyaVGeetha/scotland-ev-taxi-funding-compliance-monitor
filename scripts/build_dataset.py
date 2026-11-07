"""
Build the clean Power BI dataset for the Scotland EV Taxi Funding Compliance Risk Monitor.

Reads the official source extracts in data/raw/, validates them, harmonises council
names to ONS codes, and writes tidy tables to data/clean/ plus a data-quality log.

Run:  python scripts/build_dataset.py
"""
from pathlib import Path
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------
# Council lookup: 32 Scottish council areas (ONS S12 codes) and the name variants used
# by each source.
# --------------------------------------------------------------------------------------
COUNCILS = [
    ("S12000033", "Aberdeen City", []),
    ("S12000034", "Aberdeenshire", []),
    ("S12000041", "Angus", []),
    ("S12000035", "Argyll and Bute", ["Argyll & Bute"]),
    ("S12000036", "City of Edinburgh", ["Edinburgh, City of"]),
    ("S12000005", "Clackmannanshire", []),
    ("S12000006", "Dumfries and Galloway", ["Dumfries & Galloway"]),
    ("S12000042", "Dundee City", []),
    ("S12000008", "East Ayrshire", []),
    ("S12000045", "East Dunbartonshire", []),
    ("S12000010", "East Lothian", []),
    ("S12000011", "East Renfrewshire", []),
    ("S12000014", "Falkirk", []),
    ("S12000047", "Fife", []),
    ("S12000049", "Glasgow City", ["Glasgow, City of"]),
    ("S12000017", "Highland", []),
    ("S12000018", "Inverclyde", []),
    ("S12000019", "Midlothian", []),
    ("S12000020", "Moray", []),
    ("S12000013", "Na h-Eileanan Siar", ["Eilean Siar", "Na H-Eileanan Siar"]),
    ("S12000021", "North Ayrshire", []),
    ("S12000050", "North Lanarkshire", []),
    ("S12000023", "Orkney Islands", []),
    ("S12000048", "Perth and Kinross", ["Perth & Kinross"]),
    ("S12000038", "Renfrewshire", []),
    ("S12000026", "Scottish Borders", []),
    ("S12000027", "Shetland Islands", []),
    ("S12000028", "South Ayrshire", []),
    ("S12000029", "South Lanarkshire", []),
    ("S12000030", "Stirling", []),
    ("S12000039", "West Dunbartonshire", []),
    ("S12000040", "West Lothian", []),
]
SCOTLAND = "S92000003"

NAME_TO_CODE = {}
for code, name, aliases in COUNCILS:
    for n in [name, *aliases]:
        NAME_TO_CODE[n.lower()] = code
NAME_TO_CODE["scotland"] = SCOTLAND


def to_code(raw_name: str) -> str:
    """Strip footnote markers like '[note 10]' and map a published name to its ONS code."""
    clean = re.sub(r"\[[^\]]*\]", "", str(raw_name)).strip()
    code = NAME_TO_CODE.get(clean.lower())
    if code is None:
        raise ValueError(f"Unknown council name: {raw_name!r}")
    return code


def to_number(value):
    """Return a float, or NaN for suppressed/unavailable markers."""
    if value is None:
        return np.nan
    s = str(value).strip().replace(",", "")
    if s == "" or s.startswith("[") or s in {"-", "N/A"}:
        return np.nan
    return float(s)


dq = []  # data-quality log rows


def sev_for(diff):
    """Differences of a few pounds are rounding in the published tables."""
    return "Low" if abs(diff) <= 5 else "High"


def log(source, period, code, check, detail, severity):
    dq.append(dict(source=source, period=period, ons_code=code, check=check, detail=detail, severity=severity))


# --------------------------------------------------------------------------------------
# 1. Council dimension
# --------------------------------------------------------------------------------------
dim_council = pd.DataFrame([(c, n) for c, n, _ in COUNCILS], columns=["ons_code", "council"])
dim_council["is_island_council"] = dim_council["ons_code"].isin(["S12000013", "S12000023", "S12000027"])
dim_council.sort_values("council").to_csv(CLEAN / "dim_council.csv", index=False)

# --------------------------------------------------------------------------------------
# 2. Taxi and private hire fleet (Scottish Transport Statistics Table 1.4, 2021-2025)
# --------------------------------------------------------------------------------------
sts = pd.read_csv(RAW / "sts_table_1_4_taxis_by_council.csv", dtype=str)
sts["ons_code"] = sts["council_as_published"].map(to_code)
num_cols = ["taxi_vehicles", "private_hire_cars", "total_vehicles", "taxi_driver_licences",
            "private_hire_licences", "total_licences", "wheelchair_accessible_taxis", "wheelchair_accessible_phc"]
for c in num_cols:
    sts[c + "_raw"] = sts[c]
    sts[c] = sts[c].map(to_number)
sts["year"] = sts["edition_year"].astype(int)
src = "Scottish Transport Statistics Table 1.4"

councils_only = sts[sts["ons_code"] != SCOTLAND].copy()
councils_only["quality_flag"] = ""


def add_flag(idx, text):
    cur = councils_only.at[idx, "quality_flag"]
    councils_only.at[idx, "quality_flag"] = text if not cur else cur + "; " + text


for idx, r in councils_only.iterrows():
    if np.isnan(r["taxi_vehicles"]):
        log(src, r["year"], r["ons_code"], "Missing value", "Taxi/PHC vehicle counts published as unavailable", "Medium")
        add_flag(idx, "unavailable")
        continue
    if r["taxi_vehicles"] + r["private_hire_cars"] != r["total_vehicles"]:
        log(src, r["year"], r["ons_code"], "Total does not add up",
            f"taxis {int(r['taxi_vehicles'])} + PHC {int(r['private_hire_cars'])} = "
            f"{int(r['taxi_vehicles'] + r['private_hire_cars'])}, published total {int(r['total_vehicles'])}", "High")
        add_flag(idx, "total mismatch")
    if not np.isnan(r["taxi_driver_licences"]) and not np.isnan(r["private_hire_licences"]):
        if r["taxi_driver_licences"] + r["private_hire_licences"] != r["total_licences"]:
            log(src, r["year"], r["ons_code"], "Licence total does not add up",
                f"{int(r['taxi_driver_licences'])} + {int(r['private_hire_licences'])} != {int(r['total_licences'])}", "Low")

# Identical rows for two different councils in the same year (copy-paste error in source)
key_cols = ["taxi_vehicles", "private_hire_cars", "total_vehicles", "taxi_driver_licences", "total_licences"]
for year, grp in councils_only.dropna(subset=["taxi_vehicles"]).groupby("year"):
    dup = grp[grp.duplicated(subset=key_cols, keep=False)]
    for sig, g in dup.groupby(key_cols):
        names = ", ".join(dim_council.set_index("ons_code").loc[g["ons_code"], "council"])
        for idx in g.index:
            log(src, year, councils_only.at[idx, "ons_code"], "Duplicate row",
                f"Identical figures published for: {names}", "High")
            add_flag(idx, "duplicate row")

# Large year-on-year swings in taxi vehicles (>= 35% and >= 50 vehicles)
for code, g in councils_only.sort_values("year").groupby("ons_code"):
    prev = None
    for idx, r in g.iterrows():
        if prev is not None and not np.isnan(r["taxi_vehicles"]) and not np.isnan(prev["taxi_vehicles"]):
            change = r["taxi_vehicles"] - prev["taxi_vehicles"]
            if abs(change) >= 50 and abs(change) / prev["taxi_vehicles"] >= 0.35:
                log(src, r["year"], code, "Large year-on-year swing",
                    f"Taxi vehicles {int(prev['taxi_vehicles'])} ({prev['year']}) -> {int(r['taxi_vehicles'])} ({r['year']})",
                    "Medium")
                add_flag(idx, "large swing")
        prev = r

councils_only["is_reliable"] = ~councils_only["quality_flag"].str.contains("unavailable|total mismatch|duplicate row")
fleet = councils_only[["ons_code", "year", "taxi_vehicles", "private_hire_cars", "total_vehicles",
                       "wheelchair_accessible_taxis", "quality_flag", "is_reliable"]]
fleet.to_csv(CLEAN / "fact_taxi_fleet.csv", index=False)

scot_fleet = sts[sts["ons_code"] == SCOTLAND][["year", "taxi_vehicles", "private_hire_cars", "total_vehicles"]]
scot_fleet.to_csv(CLEAN / "fact_taxi_fleet_scotland.csv", index=False)

# --------------------------------------------------------------------------------------
# 3. EV taxi funding by council (Energy Saving Trust LCTL statistics, to 31 Dec 2023)
# --------------------------------------------------------------------------------------
est = pd.read_csv(RAW / "est_lctl_funding_by_council_to_2023-12-31.csv")
streams = ["business", "domestic", "hackney", "switched_on_taxis", "used_ev_business", "used_ev_domestic"]
est[streams] = est[streams].fillna(0)
total_row = est[est["council_as_published"] == "GRAND TOTAL"].iloc[0]
est = est[est["council_as_published"] != "GRAND TOTAL"].copy()
src = "EST Low Carbon Transport Loan statistics (by council)"
for _, r in est.iterrows():
    if abs(r[streams].sum() - r["total"]) > 2:
        log(src, "2011/12-2023/24", to_code(r["council_as_published"]), "Row total check",
            f"Streams sum {r[streams].sum():,.0f} vs total {r['total']:,.0f}", "High")
for s in streams + ["total"]:
    diff = est[s].sum() - total_row[s]
    if diff != 0:
        log(src, "2011/12-2023/24", SCOTLAND, "Column total check",
            f"{s}: councils sum {est[s].sum():,.0f} vs published {total_row[s]:,.0f}", sev_for(diff))
est["ons_code"] = est["council_as_published"].map(to_code)
est["ev_taxi_funding_gbp"] = est["hackney"] + est["switched_on_taxis"]
funding = est.rename(columns={"hackney": "hackney_loans_gbp", "switched_on_taxis": "switched_on_taxis_gbp",
                              "total": "all_lctl_loans_gbp"})[
    ["ons_code", "hackney_loans_gbp", "switched_on_taxis_gbp", "ev_taxi_funding_gbp", "all_lctl_loans_gbp"]]
funding.to_csv(CLEAN / "fact_ev_taxi_funding_by_council.csv", index=False)

# --------------------------------------------------------------------------------------
# 4. Funding by financial year and stream (EST, to 31 Mar 2024)
# --------------------------------------------------------------------------------------
fy = pd.read_csv(RAW / "est_lctl_funding_by_year_to_2024-03-31.csv")
fy_total = fy[fy["financial_year"] == "GRAND TOTAL"].iloc[0]
fy = fy[fy["financial_year"] != "GRAND TOTAL"].copy()
fy[streams] = fy[streams].fillna(0)
src = "EST Low Carbon Transport Loan statistics (by year)"
for _, r in fy.iterrows():
    if abs(r[streams].sum() - r["total"]) > 2:
        log(src, r["financial_year"], SCOTLAND, "Row total check",
            f"Streams sum {r[streams].sum():,.0f} vs total {r['total']:,.0f}", "High")
for s in streams + ["total"]:
    diff = fy[s].sum() - fy_total[s]
    if diff != 0:
        log(src, "all years", SCOTLAND, "Column total check",
            f"{s}: sum of years {fy[s].sum():,.0f} vs published grand total {fy_total[s]:,.0f}", sev_for(diff))
labels = {"business": "Business", "domestic": "Domestic", "hackney": "Hackney (EV taxi)",
          "switched_on_taxis": "Switched On Taxis (EV taxi)", "used_ev_business": "Used EV business",
          "used_ev_domestic": "Used EV domestic"}
fy_long = fy.melt(id_vars="financial_year", value_vars=streams, var_name="stream_key", value_name="amount_gbp")
fy_long["stream"] = fy_long["stream_key"].map(labels)
fy_long["is_ev_taxi_stream"] = fy_long["stream_key"].isin(["hackney", "switched_on_taxis"])
fy_long["fy_start_year"] = fy_long["financial_year"].str[:4].astype(int)
fy_long[["financial_year", "fy_start_year", "stream", "is_ev_taxi_stream", "amount_gbp"]].to_csv(
    CLEAN / "fact_funding_by_year.csv", index=False)

# --------------------------------------------------------------------------------------
# 5. Loan counts 2022/23 (Transport Scotland FOI 202300344586)
# --------------------------------------------------------------------------------------
foi = pd.read_csv(RAW / "foi_202300344586_loan_counts_2022_23.csv")
foi_total = foi[foi["council_as_published"] == "Grand Total"].iloc[0]
foi = foi[foi["council_as_published"] != "Grand Total"].copy()
cnt_cols = ["business", "domestic", "switched_on_taxis", "used_ev_domestic", "used_ev_business"]
src = "Transport Scotland FOI 202300344586"
for _, r in foi.iterrows():
    if r[cnt_cols].sum() != r["grand_total"]:
        log(src, "2022/23", to_code(r["council_as_published"]), "Row total check",
            f"{r[cnt_cols].sum()} vs {r['grand_total']}", "High")
for c in cnt_cols + ["grand_total"]:
    if foi[c].sum() != foi_total[c]:
        log(src, "2022/23", SCOTLAND, "Column total check", f"{c}: {foi[c].sum()} vs {foi_total[c]}", "High")
foi["ons_code"] = foi["council_as_published"].map(to_code)
foi.rename(columns={"switched_on_taxis": "sot_loans_2022_23", "grand_total": "all_loans_2022_23"})[
    ["ons_code", "sot_loans_2022_23", "all_loans_2022_23"]].to_csv(CLEAN / "fact_loan_counts_2022_23.csv", index=False)

# --------------------------------------------------------------------------------------
# 6. Licensed plug-in cars (DfT VEH0142, year-end Q4 2020-2025 plus 2026 Q2)
# --------------------------------------------------------------------------------------
veh = pd.read_csv(RAW / "dft_veh0142_scotland_cars_q4.csv")
periods = [c for c in veh.columns if re.match(r"\d{4}Q\d", c)]
src = "DfT VEH0142 (cars)"
for fuel, g in veh.groupby("fuel"):
    for p in periods:
        piv = g.pivot_table(index="ons_code", columns="keepership", values=p, aggfunc="sum")
        bad = piv[(piv["Company"] + piv["Private"]) != piv["Total"]]
        for code in bad.index:
            log(src, p, code, "Keepership total check", f"{fuel}: company + private != total", "Low")
        councils_sum = g[(g["ons_code"] != SCOTLAND) & (g["keepership"] == "Total")][p].sum()
        scot_val = g[(g["ons_code"] == SCOTLAND) & (g["keepership"] == "Total")][p].iloc[0]
        if councils_sum != scot_val:
            log(src, p, SCOTLAND, "Council sum vs Scotland",
                f"{fuel}: councils {councils_sum} vs Scotland {scot_val} (difference = unallocated postcodes)", "Low")
veh_long = veh.melt(id_vars=["fuel", "keepership", "ons_code", "area"], value_vars=periods,
                    var_name="period", value_name="vehicles")
veh_long["year"] = veh_long["period"].str[:4].astype(int)
veh_long["is_year_end"] = veh_long["period"].str.endswith("Q4")
veh_long["fuel"] = veh_long["fuel"].replace({"Total": "All plug-in", "Battery electric": "Battery electric"})
veh_long[["ons_code", "period", "year", "is_year_end", "fuel", "keepership", "vehicles"]].to_csv(
    CLEAN / "fact_plugin_cars.csv", index=False)

# --------------------------------------------------------------------------------------
# 7. Council compliance-risk indicators
#    These rank where an auditor should look first. They are NOT evidence of misuse.
# --------------------------------------------------------------------------------------
f = fleet.set_index(["ons_code", "year"])


def fleet_value(code, years):
    """First reliable total-vehicle figure among the given years."""
    for y in years:
        if (code, y) in f.index:
            row = f.loc[(code, y)]
            if row["is_reliable"]:
                return row["total_vehicles"], y
    return np.nan, None


rows = []
for code, name, _ in COUNCILS:
    fund = funding.set_index("ons_code").loc[code]
    base_v, base_y = fleet_value(code, [2021, 2022, 2023])
    latest_v, latest_y = fleet_value(code, [2025, 2024])
    ref_v, ref_y = fleet_value(code, [2024, 2025, 2023])
    gaps = int((~fleet[fleet["ons_code"] == code]["is_reliable"]).sum())
    swings = int(fleet[fleet["ons_code"] == code]["quality_flag"].str.contains("large swing").sum())
    bev_priv = veh_long[(veh_long["ons_code"] == code) & (veh_long["fuel"] == "Battery electric") &
                        (veh_long["keepership"] == "Private") & veh_long["is_year_end"]].set_index("year")["vehicles"]
    rows.append(dict(
        ons_code=code,
        ev_taxi_funding_gbp=fund["ev_taxi_funding_gbp"],
        fleet_reference_year=ref_y,
        licensed_taxi_phc_vehicles=ref_v,
        funding_per_licensed_vehicle_gbp=(fund["ev_taxi_funding_gbp"] / ref_v) if ref_v and ref_v > 0 else np.nan,
        fleet_baseline_year=base_y,
        fleet_latest_year=latest_y,
        fleet_change_pct=((latest_v - base_v) / base_v * 100) if base_v and not np.isnan(base_v) and not np.isnan(latest_v) else np.nan,
        unreliable_fleet_years=gaps,
        large_swing_years=swings,
        private_bev_growth_pct_2021_2025=(bev_priv[2025] - bev_priv[2021]) / bev_priv[2021] * 100,
    ))
risk = pd.DataFrame(rows)
funded = risk["ev_taxi_funding_gbp"] > 0


def pct_rank(series):
    return series.rank(pct=True, method="average") * 100


risk["score_funding_exposure"] = np.where(funded, pct_rank(risk.loc[funded, "funding_per_licensed_vehicle_gbp"]).reindex(risk.index), np.nan)
risk["score_fleet_contraction"] = np.where(funded, pct_rank(-risk.loc[funded, "fleet_change_pct"]).reindex(risk.index), np.nan)
risk["score_data_gaps"] = np.where(funded, pct_rank(risk.loc[funded, "unreliable_fleet_years"] + risk.loc[funded, "large_swing_years"]).reindex(risk.index), np.nan)
risk["audit_priority_score"] = (0.5 * risk["score_funding_exposure"].fillna(0)
                                + 0.3 * risk["score_fleet_contraction"].fillna(50)
                                + 0.2 * risk["score_data_gaps"].fillna(0)).where(funded)
risk["audit_priority_tier"] = np.select(
    [~funded, risk["audit_priority_score"] >= 70, risk["audit_priority_score"] >= 45],
    ["No EV taxi funding", "Higher", "Medium"], default="Lower")
risk["audit_priority_rank"] = risk["audit_priority_score"].rank(ascending=False, method="min")
risk = risk.merge(dim_council, on="ons_code").sort_values("audit_priority_rank")
for c in ["funding_per_licensed_vehicle_gbp", "fleet_change_pct", "private_bev_growth_pct_2021_2025",
          "score_funding_exposure", "score_fleet_contraction", "score_data_gaps", "audit_priority_score"]:
    risk[c] = risk[c].round(1)
risk.to_csv(CLEAN / "council_risk_indicators.csv", index=False)

# --------------------------------------------------------------------------------------
# 8. Data-quality log
# --------------------------------------------------------------------------------------
dq_df = pd.DataFrame(dq).merge(dim_council[["ons_code", "council"]], on="ons_code", how="left")
dq_df["council"] = dq_df["council"].fillna("Scotland")
dq_df.to_csv(CLEAN / "data_quality_log.csv", index=False)

print(f"Councils: {len(dim_council)}")
print(f"Fleet rows: {len(fleet)} | reliable: {int(fleet['is_reliable'].sum())}")
print(f"Funding rows: {len(funding)} | EV taxi funding total: £{funding['ev_taxi_funding_gbp'].sum():,.0f}")
print(f"Plug-in rows: {len(veh_long)}")
print(f"Data-quality issues logged: {len(dq_df)}")
print(dq_df.groupby(['source', 'check']).size().to_string())
