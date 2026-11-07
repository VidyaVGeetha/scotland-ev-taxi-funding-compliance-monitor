"""Static README charts generated from data/clean. Run after build_dataset.py."""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "images"
OUT.mkdir(exist_ok=True)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "Helvetica", "Arial", "DejaVu Sans"],
    "svg.fonttype": "none", "svg.hashsalt": "evtaxi", "font.size": 10, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def title(ax, main, sub):
    ax.set_title(main, loc="left", fontsize=13, fontweight="bold", color=INK, pad=24)
    ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")


def footer(fig, text):
    fig.text(0.01, 0.01, text, fontsize=8, color=INK2)


dim = pd.read_csv(CLEAN / "dim_council.csv")

# 1. EV taxi loan funding by year ---------------------------------------------------
fy = pd.read_csv(CLEAN / "fact_funding_by_year.csv")
taxi = fy[fy["is_ev_taxi_stream"]].pivot(index="financial_year", columns="stream", values="amount_gbp").fillna(0)
taxi = taxi.loc[[y for y in taxi.index if int(y[:4]) >= 2016]] / 1e6
fig, ax = plt.subplots(figsize=(9, 4.8))
x = range(len(taxi))
h = taxi["Hackney (EV taxi)"]
s = taxi["Switched On Taxis (EV taxi)"]
ax.bar(x, h, color=BLUE, width=0.62, label="Hackney loan", edgecolor=SURFACE, linewidth=2)
ax.bar(x, s, bottom=h, color=ORANGE, width=0.62, label="Switched On Taxis loan", edgecolor=SURFACE, linewidth=2)
for i, tot in enumerate(h + s):
    ax.text(i, tot + 0.12, f"£{tot:.1f}m", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(list(x), taxi.index)
ax.set_ylabel("£ million")
ax.grid(axis="x", visible=False)
ax.legend(frameon=False, loc="upper right")
title(ax, "EV taxi loans paid in Scotland by financial year",
      "Energy Saving Trust Low Carbon Transport Loan, taxi streams only")
footer(fig, "Source: Energy Saving Trust LCTL statistics to 31 March 2024. 2023/24 includes used-vehicle Switched On Taxis loans.")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "01_ev_taxi_funding_by_year.svg")
plt.close(fig)

# 2. Funding per licensed taxi/PHC vehicle --------------------------------------------
risk = pd.read_csv(CLEAN / "council_risk_indicators.csv")
r = risk[risk["ev_taxi_funding_gbp"] > 0].sort_values("funding_per_licensed_vehicle_gbp").tail(15)
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(r["council"], r["funding_per_licensed_vehicle_gbp"], color=BLUE, height=0.62)
for i, v in enumerate(r["funding_per_licensed_vehicle_gbp"]):
    ax.text(v + 150, i, f"£{v:,.0f}", va="center", fontsize=8.5, color=INK2)
ax.set_xlabel("£ of EV taxi loans per licensed taxi + private hire vehicle")
ax.grid(axis="y", visible=False)
ax.set_xlim(0, r["funding_per_licensed_vehicle_gbp"].max() * 1.15)
title(ax, "Where EV taxi funding is high relative to the licensed fleet",
      "Top 15 councils. Loans are recorded by the borrower's address, so commuter councils can look high")
footer(fig, "Sources: EST LCTL statistics (cumulative); Scottish Transport Statistics Table 1.4 (2024 fleet).")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "02_funding_per_licensed_vehicle.svg")
plt.close(fig)

# 3. Scotland fleet trend ---------------------------------------------------------------
sf = pd.read_csv(CLEAN / "fact_taxi_fleet_scotland.csv").sort_values("year")
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(sf["year"], sf["private_hire_cars"], color=ORANGE, lw=2, marker="o", ms=7, mec=SURFACE, mew=2)
ax.plot(sf["year"], sf["taxi_vehicles"], color=BLUE, lw=2, marker="o", ms=7, mec=SURFACE, mew=2)
ax.text(2025.12, sf["private_hire_cars"].iloc[-1], "Private hire cars", va="center", color=INK2, fontsize=9)
ax.text(2025.12, sf["taxi_vehicles"].iloc[-1], "Taxis", va="center", color=INK2, fontsize=9)
ax.set_xticks(sf["year"])
ax.set_xlim(2020.8, 2025.9)
ax.set_ylim(0, sf["private_hire_cars"].max() * 1.15)
ax.set_ylabel("Licensed vehicles")
ax.grid(axis="x", visible=False)
title(ax, "Licensed taxis and private hire cars in Scotland, 2021–2025",
      "Private hire grew 34%; taxis moved between 7,600 and 9,300 with no clear trend")
footer(fig, "Source: Scottish Transport Statistics Table 1.4 (Scotland totals as published).")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "03_scotland_fleet_trend.svg")
plt.close(fig)

# 4. Audit priority matrix ----------------------------------------------------------------
m = risk[risk["ev_taxi_funding_gbp"] > 0].dropna(subset=["fleet_change_pct"])
fig, ax = plt.subplots(figsize=(9, 6))
colors = m["audit_priority_tier"].map({"Higher": ORANGE, "Medium": BLUE, "Lower": "#9a9993"})
ax.scatter(m["funding_per_licensed_vehicle_gbp"], m["fleet_change_pct"], s=70, c=colors,
           edgecolors=SURFACE, linewidths=2, zorder=3)
ax.set_xscale("log")
ax.axhline(0, color=INK2, lw=0.8)
for _, row in m.iterrows():
    if row["audit_priority_tier"] == "Higher" or row["funding_per_licensed_vehicle_gbp"] > 2500:
        offset, ha = {"West Lothian": ((-8, 4), "right"), "Angus": ((6, 6), "left"),
                      "Glasgow City": ((6, -10), "left"), "Dundee City": ((40, -40), "left")}.get(
            row["council"], ((6, 4), "left"))
        ax.annotate(row["council"], (row["funding_per_licensed_vehicle_gbp"], row["fleet_change_pct"]),
                    xytext=offset, textcoords="offset points", fontsize=8.5, color=INK, ha=ha,
                    arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6) if row["council"] == "Dundee City" else None)
for lbl, col in [("Higher priority", ORANGE), ("Medium", BLUE), ("Lower", "#9a9993")]:
    ax.scatter([], [], c=col, s=50, label=lbl)
ax.legend(frameon=False, loc="upper left")
ax.set_xlabel("EV taxi loans per licensed vehicle (£, log scale)")
ax.set_ylabel("Change in licensed taxi + PHC fleet (%)")
title(ax, "Audit priority: funding exposure against fleet change",
      "Lower right = more funding per vehicle while the licensed fleet shrank. A prompt to check, not a finding")
footer(fig, "Score = 50% funding exposure + 30% fleet contraction + 20% data gaps (percentile ranks among funded councils).")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "04_audit_priority_matrix.svg")
plt.close(fig)
print("charts written:", sorted(p.name for p in OUT.glob("*.svg")))
