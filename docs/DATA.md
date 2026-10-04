# Data provenance and scope

Dataset: **National Transport Authority (NTA) Ireland GTFS Timetable Dataset**.

Source portal: https://www.transportforireland.ie/transitData/PT_Data.html

The supplied archive was named `GTFS_Realtime.zip`, but this application uses its **static GTFS timetable tables**, not live vehicle positions or trip updates. The original 144 MB ZIP is excluded from Git and is not required to run this snapshot.

The prepared snapshot represents **5 October 2026**, with service-calendar filtering applied. It contains 568,429 active stop events. Bounds: latitude 53.18–53.46 and longitude -6.50–-6.02. Analysis covers morning 07:00–10:00 and evening 16:00–19:00 at 2,935 same-stop interchanges, producing 70,251 eligible connection/peak records.

## Files

- `events-20261005.csv.gz`: active stop events used to rebuild results.
- `stops-20261005.csv.gz`: stops in the analysis region.
- `all-connections.csv.gz`: all eligible connection/peak records.
- `poor-transfers.csv`: the 1,308 flagged patterns.
- `improvement-scenarios.csv`: shifts 0–10 minutes for each flagged pattern.
- `transfer-index.json.gz`: arrivals/departures for interactive evidence and stop-wide checks.
- `analysis-summary.json`: scope and aggregate counts.

`build_analysis.py` rebuilds derived results from the included events and stops. It does not download or update the original feed.

## Detection and simulation

Boarding allowance: two minutes. A near-miss means being ready 1–5 minutes after a connecting departure and then waiting at least 15 minutes. A poor pattern requires at least three arrivals and at least 40% near-misses. Median waits exclude arrivals with no later service.

Suggested shifts minimise unmatched arrivals first, then median wait, then worsened arrivals, then shift size. Locations are ranked by their strongest individual connection's reduction. Shifts are independent alternatives, not a simultaneously optimised timetable.

No actual passenger demand, live reliability, nearby-stop walking transfers or network-wide operational feasibility is inferred. A route/direction group can contain variants. Counts describe the included representative weekday only. Small samples and downstream effects require validation.

## Attribution

National Transport Authority / Transport for Ireland. Contains Irish Public Sector Data licensed under Creative Commons Attribution 4.0. Derived results are calculations performed for MissingLink; they are not official NTA recommendations.
