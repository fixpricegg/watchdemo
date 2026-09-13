# WatchDemo

WatchDemo is a web application for analyzing Counter-Strike 2 demo files. It turns a `.dem` file into an interactive browser report with match statistics, player movement, timeline events, and evidence-linked coaching feedback.

> **Status:** active development, Radar v1. The technical replay core works, but the complete upload-to-report product flow is not ready yet.

## Product goal

```text
Upload a CS2 demo
        ↓
Parse the match
        ↓
Open a browser report
        ↓
See the most important problems
        ↓
Jump to the exact Radar/Timeline evidence
```

The first working version is a closed **alpha v0.1** for Inferno. A tester must be able to upload a demo, select the analyzed player, receive a report, and inspect 1–3 evidence-linked findings without developer assistance.

## Current functionality

### Demo parsing and analysis

- Round and match-start detection
- Kill and death extraction
- Pause-aware timing
- Player positions and dynamic CT/T sides by tick
- Match score across side switches and overtime
- K/D, headshot percentage, entries, multi-kills and trade kills
- Possible missed-trade events
- Rule-based Top Problems

### Interactive replay

- React Radar and Timeline
- Alive/dead states and persistent player names
- Player view direction
- Round phases, timer and score
- Event markers with jump-to-tick navigation
- Bomb lifecycle v1: carrier, dropped, planted, defused and exploded
- Grenade trajectories
- Smoke, molotov and decoy effect lifecycles

## Current focus

The current development phase is **functional Radar v1 closure**:

1. Split component styles before HUD and Kill Feed are added
2. Add HP, armor, weapon, ammo, utility and kit to tick state
3. Build an informative player hover
4. Build CT/T player HUD
5. Build a synchronized Kill Feed
6. Convert raw bomb-site values to A/B
7. Confirm the full Inferno replay flow

After Radar v1, the project freezes its JSON contracts, splits the Python monoliths, and builds the real `upload → processing → report` path.

See [ROADMAP.md](ROADMAP.md) for the complete alpha plan and [WORKFLOW.md](WORKFLOW.md) for the development process.

## Architecture

```text
CS2 demo (.dem)
        ↓
Python + demoparser2
        ↓
Deterministic replay and analysis
        ↓
radar.json + report.json
        ↓
React report, Radar and Timeline
```

The deterministic backend remains the source of truth. A future AI layer will explain verified findings and detect multi-match patterns rather than invent match events.

## Tech stack

| Area | Technology |
| --- | --- |
| Demo parsing | Python, demoparser2, pandas |
| Planned API | FastAPI, Uvicorn |
| Frontend | React, Vite |
| Data exchange | Versioned JSON contracts |

## Current limitations

- Inferno is the only configured map
- Demo path and analyzed player are still configured manually
- Generated JSON is still copied into the frontend manually
- Radar JSON is large and not optimized
- Dropped/planted C4 coordinates are approximate in some states
- Analysis rules are early heuristics
- No complete API, accounts or FACEIT integration
- No automated regression suite

## Alpha target

The alpha is ready when:

- an unfamiliar tester completes the full flow without a terminal;
- round count and final score are correct on supported demos;
- every Top Problem links to valid replay evidence;
- at least 5–10 external players can test the product;
- feedback distinguishes useful, wrong and unclear findings.

## Product rule

Do not perfect isolated features before the complete product path works.

Build the first useful WatchDemo, test it, then improve it.
