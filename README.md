# MissingLink — Transport Improvement Planner

![MissingLink project thumbnail](assets/thumbnail.png)

Find poor public transport transfers and investigate timetable changes using real Dublin NTA data.

MissingLink identifies **1,308 poor connection patterns across 595 locations**, with at least one simulated improvement at **591 locations**. It helps planners compare opportunities and inspect the timetable evidence before considering changes.

## What it does

- **Overview:** map, headline counts and five priority places.
- **All locations & results:** every finding grouped by stop, with downloads.
- **Explore a place:** compare all poor connections at the selected stop.
- **Optional simulator:** test departure delays from 0 to 10 minutes, compare waiting times and inspect the evidence.
- **Stop-wide check:** show which arrival opportunities from other incoming routes improve or worsen.

The app opens with bundled real results. No upload or date selection is needed.

## Run locally

Python 3.12 is the tested runtime.

```sh
python -m venv .venv
```

Activate the environment:

```sh
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Then run:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Windows users can also run `powershell -ExecutionPolicy Bypass -File .\run.ps1`.

## Example

At DCU Collins Avenue, a three-minute departure shift for the evening 220 → 104 connection changes simulated median waiting from 64 to 2 minutes across three scheduled arrivals. All three improve, but the same shift worsens 16 other arrival opportunities at this stop. This is a tradeoff to investigate, not an approved operational change.

## Dataset and method

**National Transport Authority (NTA) Ireland GTFS Timetable Dataset**: stops, routes, trips, stop times and service calendars.

The included snapshot uses one representative weekday with service calendars applied. It analyses same-stop transfers during morning and evening peaks, allowing two minutes for boarding. A poor pattern requires at least three incoming services and a near-miss rate of at least 40%.

See [data provenance and limitations](docs/DATA.md). Scheduled opportunities are not passenger counts, and benefits must not be added across overlapping stops.

## Rebuild and test

The prepared stop-event snapshot is included, so the original large feed is not needed to rebuild the rankings:

```sh
python build_analysis.py
python -m unittest discover -s tests -v
```

The GitHub Actions workflow runs the test suite on Python 3.12. Test fixtures are used only in tests; the product displays real timetable data.

## Optional AI explanation

The app includes an optional explanation button. It requires an OpenAI API key configured on the server; no key is included in this repository. Without it, deterministic analysis and calculated summaries remain available. AI does not calculate or change rankings. The live AI path has not been verified.

## Demo and presentation

- [2 minute 39 second walkthrough](demo/walkthrough.mp4)
- [Narration script](demo/script.txt) and [subtitles](demo/walkthrough.srt)
- [Pitch deck brief](docs/pitch-deck-brief.docx)
- [Project thumbnail](assets/thumbnail.png)

## Repository layout

```text
app.py                 Streamlit planner
engine.py              GTFS import and transfer calculations
build_analysis.py      Rebuild analysis from bundled stop events
data/                  Real snapshot, rankings and scenarios
tests/                 Import, engine, data and UI checks
assets/                Thumbnail and generation prompt
demo/                  Video, script and subtitles
docs/                  Dataset notes and presentation brief
.github/workflows/     Automated checks
```

## Hosting

This is a Python Streamlit application. It needs a Python hosting service; GitHub Pages cannot run it directly. The incomplete experimental static-site port is deliberately not included in this repository. No public app deployment has been verified.

## Attribution

Contains Irish Public Sector Data licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), attributed to the National Transport Authority. [NTA/TFI source](https://www.transportforireland.ie/transitData/PT_Data.html).

The illustration was generated with OpenAI image generation. OpenAI Codex assisted with implementation and testing. No software license has been selected; dataset licensing is separate from code licensing.
