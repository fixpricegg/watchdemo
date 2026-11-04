# WatchDemo Roadmap — alpha v0.1

WatchDemo turns CS2 demos into an interactive replay and a small number of actionable, evidence-linked findings.

This roadmap ends at the first working version: a closed Inferno-only alpha that 5–10 players can use without developer assistance. Multi-map support, accounts, FACEIT, payments and AI are later stages, not alpha blockers.

## Definition of the first working version

A tester can:

1. upload an Inferno `.dem`;
2. select the analyzed player;
3. see real processing status;
4. open Summary, Top Problems, Radar, Timeline, HUD and Kill Feed;
5. open 1–3 findings;
6. jump from every finding to the relevant replay evidence;
7. complete the flow without a terminal, manual Python edits or JSON copying.

## Fixed phase order

```text
Repository truth
→ Radar v1
→ Data contracts and backend refactor
→ Upload-to-report
→ Analysis MVP
→ Reliability and alpha preparation
→ Closed alpha
```

Work outside the current phase goes to Later unless it blocks the main scenario.

---

## Phase 0 — Repository truth

**Goal:** GitHub, documentation and the working source describe the same project.

### Tasks

- Confirm player names and view direction are merged into `main`
- Update README and this roadmap
- Close completed source-import work
- Keep exact C4 tracking separate from approximate Bomb Tracking v1
- Create one `MVP v0.1` epic issue
- Keep one active product branch at a time

### Exit gate

- `main` is runnable
- documentation matches current behavior
- open issues represent real remaining work
- no known local product change is missing from GitHub

**Estimate:** 1–2 focused sessions.

---

## Phase 1 — Functional Radar v1 closure

**Goal:** a user can understand the essential state of a complete Inferno round without opening the original CS2 demo.

### 1. Split component styles

Do this before adding HUD and Kill Feed.

```text
frontend/src/
├── App.css
├── index.css
├── components/
│   ├── Radar.css
│   ├── Timeline.css
│   └── Summary.css
```

This is a mechanical refactor. Do not redesign the interface in the same PR.

### 2. Extend player tick state

Add only verified demoparser2 fields:

- HP
- armor
- helmet
- active weapon
- ammo
- inventory/utility
- defuse kit

### 3. Player hover

Show:

- nickname and side
- alive/dead
- HP and armor
- active weapon and ammo
- utility and kit

### 4. CT/T HUD

Show both five-player teams synchronized with the current replay tick:

- alive/dead
- HP and armor
- active weapon
- utility
- kit
- C4 carrier

### 5. Kill Feed

Build from `player_death` facts:

- tick
- killer
- victim
- weapon
- headshot
- assist when available
- jump to event tick

Entry/trade labels are added later by the analysis layer.

### 6. Radar tails

- Map raw bomb-site values to A/B
- Document approximate dropped/planted C4 positions
- Use one current tick for players, bomb, grenades, HUD and Kill Feed
- Verify a complete Inferno match

### Out of scope

- final icons and visual polish
- playback speed controls
- perfect smoke/fire sizing
- exact C4 entity tracking
- other maps

### Exit gate

A complete Inferno match can be followed using Radar, Timeline, score, player names, view direction, HUD, weapons, utility, bomb, grenades and Kill Feed.

**Estimate:** 5–7 focused sessions.

---

## Phase 2 — Version data contracts and split backend monoliths

**Timing:** after Radar v1, before the API. This is the planned refactor window for both `demo_script.py` and `radar.py`.

### Data contracts

- Add `schema_version` to `radar.json` and `report.json`
- Document required and optional fields
- Add small synthetic fixtures without real SteamIDs
- Stop bundling a large real match JSON into the frontend build

### Target backend structure

```text
backend/watchdemo/
├── pipeline.py
├── config.py
├── parsing/
│   ├── demo.py
│   ├── rounds.py
│   ├── players.py
│   └── events.py
├── replay/
│   ├── radar.py
│   ├── bomb.py
│   ├── grenades.py
│   └── export.py
├── analysis/
│   ├── combat.py
│   ├── entries.py
│   ├── trades.py
│   ├── problems.py
│   └── models.py
└── reports/
    └── json_report.py
```

`demo_script.py` becomes a small CLI wrapper around the pipeline.

### Refactor rules

- One responsibility per PR
- No new product features in refactor PRs
- Keep outputs behaviorally equivalent
- Compare two known demos after each meaningful extraction
- Do not change analysis thresholds

### Exit gate

- orchestration is small and readable;
- modules have focused responsibilities;
- two control demos preserve round count, score, players, events, summary and replay states;
- frontend still consumes the same versioned contract.

**Estimate:** 5–8 focused sessions.

---

## Phase 3 — Upload-to-report product path

**Goal:** remove the developer and manual JSON copying from the user journey.

### Minimal API

- `GET /api/health`
- `POST /api/analyses`
- `GET /api/analyses/{id}/status`
- `GET /api/analyses/{id}/report`
- `GET /api/analyses/{id}/replay`

A single local worker is enough for alpha.

### Processing pipeline

```text
upload
→ validate file
→ temporary storage
→ parse
→ player selection
→ report/replay artifacts
→ ready or actionable error
→ demo cleanup
```

### Frontend pages

- Landing
- Upload and player selection
- Processing
- Report
- Error state

The Report page contains Summary, Top Problems, Radar, Timeline, HUD and Kill Feed. React receives data through the API instead of importing `src/data/radar.json`.

### Exit gate

An unfamiliar tester uploads a demo and opens the report without terminal access, code edits or file copying.

**Estimate:** 8–12 focused sessions.

---

## Phase 4 — Analysis MVP

**Goal:** answer “what should I change?” rather than only replaying the match.

Return no more than three strong findings per match.

### Initial candidates

- failed entry / early first death
- trade kill
- possible missed trade with confidence
- another repeated behavior only when it has explainable evidence

K/D and HS percentage alone are not problems.

### Finding contract

```text
id
type
title
confidence
severity
round
evidence_ticks[]
explanation
why_it_matters
recommendation
rule_version
```

A finding without valid evidence does not enter Top Problems.

### Validation

- Manually label 20–30 situations
- Record true positive, false positive and unclear
- Use High / Medium / Possible confidence
- Keep deterministic logic responsible for facts
- Use AI later only to explain verified findings

### Exit gate

Every processed match returns no more than three understandable findings, and every finding opens the correct Radar/Timeline evidence.

**Estimate:** 6–10 focused sessions.

---

## Phase 5 — Reliability and alpha preparation

This is where systematic validation belongs.

### Demo set

Run at least 10 Inferno demos covering different sources and match structures.

### Automated checks

- non-empty rounds
- `freeze_start < live_start < end`
- monotonic score
- final score matches round winners
- player tick data exists
- evidence ticks are valid
- round pairing, score, bomb state and grenade lifecycle unit tests
- one upload-to-report smoke test

### Performance and safety

- serve replay data through the API
- enable compression
- consider round-based replay chunks if needed
- define demo and generated-artifact cleanup
- handle parse and unsupported-demo errors
- document known limitations

### Alpha release gate

- at least 8 of 10 valid Inferno demos process automatically
- round count and final score are correct for every successful demo
- happy path has no manual steps
- every Top Problem evidence link works
- no known frontend crash in the supported flow

**Estimate:** 5–8 focused sessions.

---

## Phase 6 — Closed alpha

**Goal:** learn whether the product is useful, not prove market scale.

### Test

- 5–10 external players
- Inferno only
- multiple skill levels
- users complete the flow themselves
- findings can be rated `useful`, `wrong` or `unclear`

### Provisional learning gates

- 5 users complete their first analysis without help
- at least 4 of the first 5 find one useful finding
- at least 3 of the first 5 return with another demo or request another analysis
- High-confidence findings receive less than 20% `wrong` ratings on the initial sample
- every failure is classified

These are small-sample learning gates, not market statistics.

**Estimate:** 4–6 focused sessions plus feedback time.

---

## Development progress metrics

### Primary KPI

Share of phase acceptance criteria verified and merged into `main`.

### Driver metrics

- small completed PRs per week
- demos completing the full pipeline
- findings with valid evidence
- manual actions between upload and report
- processing time to ready report

### Guardrails

- `main` remains runnable
- no real `.dem`, SteamID, generated report or secret enters the public repository
- new rules do not increase obviously wrong High-confidence findings
- work-in-progress limit is one product branch

---

## Deferred until after alpha

- all maps
- accounts and password recovery
- match history and player profile
- FACEIT/Steam integration
- payments
- AI Coach and multi-match portrait
- final intro/video/design
- advanced replay controls
- exact low-level C4 entity tracking when approximate v1 is sufficient

After Phase 3, page structure and data contracts are stable enough for Kirill or the project owner to begin design in parallel while backend work continues on Analysis MVP.

## After alpha

If findings are useful:

1. fix the main sources of wrong conclusions;
2. move maps into configuration and add the active map pool;
3. improve utility and clutch analysis;
4. add accounts, history and player profile;
5. connect FACEIT;
6. add AI explanations and multi-match pattern detection;
7. consider payments only after repeat usage is demonstrated.

If findings are not useful, do not expand maps or add AI. Improve the core analysis first.

## Working rule

Before every session:

```text
Phase:
Task:
Why:
Done:
Out of scope:
```

A task is complete only after validation and merge into `main`.
