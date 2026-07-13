# WatchDemo Roadmap

WatchDemo turns CS2 demos into an interactive match replay and actionable player analysis.

The current priority is not visual polish or AI. The priority is a complete, reliable first product that users can actually test.

## Product vision

A player connects FACEIT or uploads a demo, opens a match, and receives:

- an interactive radar replay;
- match statistics;
- top mistakes with evidence;
- direct navigation to the relevant round and moment;
- explanations and better alternatives;
- a long-term player profile built from multiple matches.

AI will explain and combine verified signals. It must not invent match events.

## Current phase: Radar v1

Goal: replay one complete match reliably on Inferno.

### Done

- Player positions on radar
- CT/T colors
- Side-switch handling
- Alive/dead state
- Playback controls
- Timeline navigation
- Round phases and timer
- Match score, including overtime side switches
- Event markers and jump-to-event navigation

### Next

- Bomb carrier
- Dropped bomb
- Planted bomb
- Defuse/explosion state
- Grenade events and trajectories
- Better round navigation
- Selected-player highlighting
- More informative player tooltip

### Definition of done

Radar v1 is complete when a user can follow the essential state of every round without opening the original CS2 demo.

## Phase 2: Raw end-to-end product

Goal: complete the full user journey without manual file copying.

- Landing page
- Demo upload
- Processing state
- Error handling
- Report page
- Summary
- Top Problems
- Basic statistics
- Radar and Timeline
- Event list with evidence links

### Definition of done

A tester can upload a `.dem` file and receive a complete browser report without developer assistance.

## Phase 3: Multi-map support

Goal: make one radar engine work across the active map pool.

- Move map coordinates and assets into configuration
- Add Mirage
- Add Dust2
- Add Ancient
- Add Nuke
- Add Anubis
- Add remaining relevant maps
- Verify coordinates, orientation, levels, bomb and grenades on every map

## Phase 4: Analysis quality

Goal: make findings trustworthy enough to guide player decisions.

- Build a test set of demos
- Manually review detected mistakes
- Measure false positives
- Add confidence levels
- Improve trade analysis
- Improve entry analysis
- Add utility analysis
- Add clutch analysis
- Connect every complex finding to replay evidence

## Phase 5: Design handoff

Before handoff to frontend/design work:

- Freeze `radar.json` and `report.json` contracts
- Document required and optional fields
- Confirm page structure
- Provide representative mock data
- Separate backend and frontend responsibilities

While frontend design is in progress, backend work continues on analysis quality and new metrics.

## Phase 6: Accounts and integrations

- User accounts
- FACEIT connection
- Recent matches
- Match history
- Player profile
- Progress over time

## Phase 7: AI layer

- Match summaries
- Multi-match pattern detection
- Personalized explanations
- Training recommendations
- Conversational questions about a match

AI consumes structured, verified analysis. Deterministic backend logic remains the source of truth.

## Testing target before public release

- 5–10 external testers for the first raw version
- Multiple skill levels
- Multiple demos per tester
- Feedback on usefulness and wrong conclusions
- Repeat usage after the first analysis

## Product rule

Do not perfect isolated features before the complete product path works.

Build the first useful WatchDemo, test it, then improve it.
