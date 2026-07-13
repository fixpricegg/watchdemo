# WatchDemo

WatchDemo is a web application for analyzing Counter-Strike 2 demo files. It turns a `.dem` file into an interactive browser report with match statistics, player movement, timeline events, and evidence-linked coaching feedback.

> **Status:** active development, early MVP. The parser, first analysis rules, report generation, interactive radar, Timeline, score tracking, and event navigation are working. The product is not ready for public release yet.

## Product goal

```text
Upload a CS2 demo
        ↓
Parse the match
        ↓
Open a browser report
        ↓
Inspect statistics, mistakes, and the exact replay moment
```

WatchDemo is intended for competitive players who want to improve but do not want to manually review every round or pay for a personal coach.

## Current functionality

### Demo parsing

- Round and match-start detection
- Kill and death extraction
- Invalid world-death filtering
- Pause-aware timing
- Player positions by tick
- Dynamic CT/T side detection
- Round-end winner detection
- Match score tracking across side switches and overtime

### Player analysis

- Kills, deaths, and K/D
- Headshot percentage
- Entry kills and entry deaths
- Entry success rate
- Average opening-kill and first-death timing
- Multi-kill rounds
- Trade kills
- Possible missed-trade events
- Rule-based Top Problems

### Interactive report

- React radar playback
- Alive/dead player states
- CT/T colors that update after side switches
- Timeline with round segments
- Buy and Live phases
- Round timer
- Current score
- Event markers
- Click-to-jump from an event to the closest replay tick

## Current focus

The current development phase is **Radar v1** on Inferno.

Next priorities:

1. Bomb carrier, dropped bomb, planted bomb, defuse, and explosion states
2. Grenade events and trajectories
3. Better round navigation and player focus
4. Complete raw user flow from upload to report
5. Multi-map support
6. Analysis-quality testing with real demos

See [ROADMAP.md](ROADMAP.md) for the full plan and [WORKFLOW.md](WORKFLOW.md) for the development process.

## Architecture

```text
CS2 demo (.dem)
        ↓
Python + demoparser2
        ↓
Deterministic match analysis
        ↓
radar.json + report.json
        ↓
React report, Radar, and Timeline
```

The deterministic backend is the source of truth. A future AI layer will explain verified signals, compare matches, and personalize recommendations rather than invent match events.

## Tech stack

| Area | Technology |
| --- | --- |
| Demo parsing | Python, demoparser2, pandas |
| Backend | FastAPI, Uvicorn |
| Frontend | React, Vite |
| Data exchange | JSON |

## Planned repository structure

```text
watchdemo/
├── backend/
│   ├── app/
│   ├── analyzer/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
├── README.md
├── ROADMAP.md
├── WORKFLOW.md
└── .gitignore
```

The current local source will be added after the working version is reviewed and sensitive or generated files are excluded.

## Current limitations

- Inferno is the only configured radar map
- Radar JSON is large and not yet optimized
- Some analysis rules are still coarse heuristics
- Missed-trade detection does not yet understand walls, vision, flashes, reloads, or team intent
- No complete upload-to-report flow is deployed
- No user accounts or FACEIT integration
- No automated regression suite yet

## Testing strategy

Before public release, the first complete version will be tested with 5–10 external players. The important signals are:

- successful demo-processing rate;
- correctness of replay state;
- false-positive rate for detected mistakes;
- whether users open evidence moments;
- whether users return to analyze another match.

## Product rule

Do not perfect isolated features before the complete product path works.

Build the first useful WatchDemo, test it, then improve it.
