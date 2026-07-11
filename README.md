# WatchDemo

WatchDemo is a web application for analyzing Counter-Strike 2 demo files. Upload a demo, select a player, and inspect match statistics, entry performance, round timing, and player movement on an interactive radar.

> **Status:** active development — early MVP. The core parser, API, report generation, and first radar version are working. The project is not production-ready yet.

## Why WatchDemo?

Scoreboards show the result of a match, but they rarely explain how it happened. WatchDemo is being built to turn raw CS2 demos into clear, actionable feedback without requiring players to review every round manually.

The MVP goal is simple:

```
Upload a .dem file → process the match → receive a useful browser report
```

## Implemented

### Demo parsing

- Round start and round end detection
- Final score and winning team
- Player scoreboard statistics
- Kill and death event extraction
- Filtering of invalid world deaths
- Player coordinates across the match
- Pause-aware round timing

### Player statistics

- Kills and deaths
- K/D ratio
- Headshot percentage
- MVPs
- 3K, 4K, and ace counts
- Entry kills and entry deaths
- Entry success rate
- Average timing of the first opening kill
- Average timing of the first death

### Web application

- FastAPI endpoint for demo uploads
- Parsed data returned as JSON
- Markdown report generation
- Player selection
- Interactive round radar
- Alive/dead player states
- Round playback controls

## In progress

- A radar closer to the native CS2 look and behavior
- Smoother and more informative radar playback
- Score display for each round
- Hover previews and faster round navigation
- Better visual design and report layout
- More reliable handling of edge cases in demos

## Planned MVP

- Match summary with ADR, K/D, entry performance, and utility usage
- Automatic detection of the player's most important mistakes
- Top five problems ranked by impact
- One or two concrete round examples with timestamps
- Clear recommendations that a player can apply in future matches

## Tech stack

| Area | Technology |
| --- | --- |
| Demo parsing | Python, demoparser2, pandas |
| Backend | FastAPI, Uvicorn |
| Frontend | React |
| Data exchange | JSON |

## Architecture

```text
CS2 demo (.dem)
      ↓
Python parser
      ↓
Structured match data
      ↓
FastAPI
      ↓
React report and radar
```

## Current limitations

- The analyzer is still under active development.
- Only part of the planned coaching analysis is implemented.
- Large radar datasets can take noticeable time to load.
- The public repository does not yet contain the full application source code or setup instructions.

## Roadmap

1. Finish the round radar and navigation.
2. Add remaining core match metrics.
3. Build the first rule-based mistake detector.
4. Generate actionable player reports with round evidence.
5. Improve performance, error handling, and UI.
6. Prepare a testable public MVP.

## Author

Created by [Marko Petkovich](https://github.com/fixpricegg).
