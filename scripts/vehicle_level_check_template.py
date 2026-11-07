"""
Vehicle-level follow-up check — TEMPLATE for an authorised funder or auditor ONLY.

The open data in this repo cannot say whether any individual vehicle was misused. A
body that already holds the funded vehicle list lawfully (for example the scheme
administrator, or a council licensing team) can run this script to see which funded
vehicles had a new V5C logbook issued soon after funding. A new V5C is issued when the
keeper changes, and also for other reasons (change of address, name, plates or colour),
so a flag means "look at this file", never "this was misused".

You need:
  * a DVLA Vehicle Enquiry Service API key (apply at developer-portal.driver-vehicle-licensing.api.gov.uk)
  * data/private/funded_vehicles.csv with columns:
        loan_id, vrm, loan_date (YYYY-MM-DD), licensing_council,
        licence_end_date (YYYY-MM-DD, blank if still licensed)
  * a lawful basis under UK GDPR to process the registrations. This repository does
    NOT contain and must never contain registration numbers.

Run:
  export DVLA_VES_API_KEY=...
  python scripts/vehicle_level_check_template.py --months 24

Output (written to data/private/, which is git-ignored):
  vehicle_flags.csv        full detail for the case team
  vehicle_flags_summary.csv  counts by council, safe to share
"""
import argparse
import hashlib
import json
import os
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "data" / "private"
VES_URL = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"


def ves_lookup(vrm: str, api_key: str) -> dict:
    body = json.dumps({"registrationNumber": vrm.replace(" ", "").upper()}).encode()
    req = urllib.request.Request(VES_URL, data=body, method="POST",
                                 headers={"x-api-key": api_key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def months_between(a: date, b: date) -> float:
    return (b - a).days / 30.44


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=24, help="window after loan date to flag a V5C reissue")
    ap.add_argument("--sleep", type=float, default=0.25, help="pause between API calls (be polite)")
    args = ap.parse_args()

    api_key = os.environ.get("DVLA_VES_API_KEY")
    if not api_key:
        raise SystemExit("Set DVLA_VES_API_KEY first.")
    src = PRIVATE / "funded_vehicles.csv"
    if not src.exists():
        raise SystemExit(f"Missing {src}. See the docstring for the expected columns.")

    df = pd.read_csv(src, dtype=str)
    out = []
    for _, r in df.iterrows():
        rec = {"loan_id": r["loan_id"], "licensing_council": r["licensing_council"],
               "vrm_hash": hashlib.sha256(r["vrm"].replace(" ", "").upper().encode()).hexdigest()[:16]}
        try:
            v = ves_lookup(r["vrm"], api_key)
        except Exception as exc:  # noqa: BLE001 - record and continue
            rec["lookup_error"] = str(exc)
            out.append(rec)
            continue
        loan_dt = datetime.strptime(r["loan_date"], "%Y-%m-%d").date()
        v5c = v.get("dateOfLastV5CIssued")
        v5c_dt = datetime.strptime(v5c, "%Y-%m-%d").date() if v5c else None
        lic_end = r.get("licence_end_date")
        lic_end_dt = datetime.strptime(lic_end, "%Y-%m-%d").date() if isinstance(lic_end, str) and lic_end else None

        rec.update({
            "fuel_type": v.get("fuelType"),
            "first_registered": v.get("monthOfFirstRegistration"),
            "tax_status": v.get("taxStatus"),
            "date_last_v5c": v5c,
            "months_loan_to_v5c": round(months_between(loan_dt, v5c_dt), 1) if v5c_dt else None,
            "licence_ended": bool(lic_end_dt),
            "months_loan_to_licence_end": round(months_between(loan_dt, lic_end_dt), 1) if lic_end_dt else None,
        })
        v5c_soon = v5c_dt is not None and 0 <= months_between(loan_dt, v5c_dt) <= args.months
        rec["signal_v5c_reissued_in_window"] = v5c_soon
        rec["signal_not_electric"] = (v.get("fuelType") or "").upper() not in {"ELECTRICITY", "ELECTRIC"}
        rec["signal_licence_ended_in_window"] = (lic_end_dt is not None
                                                 and months_between(loan_dt, lic_end_dt) <= args.months)
        rec["review_priority"] = ("Review" if v5c_soon and rec["signal_licence_ended_in_window"]
                                  else "Check" if v5c_soon or rec["signal_licence_ended_in_window"]
                                  else "No signal")
        out.append(rec)
        time.sleep(args.sleep)

    res = pd.DataFrame(out)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    res.to_csv(PRIVATE / "vehicle_flags.csv", index=False)
    summary = res.groupby(["licensing_council", "review_priority"]).size().unstack(fill_value=0)
    summary.to_csv(PRIVATE / "vehicle_flags_summary.csv")
    print(summary)


if __name__ == "__main__":
    main()
