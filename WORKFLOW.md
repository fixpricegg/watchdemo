# Development Workflow

## Source of truth

- `main` contains the latest stable version.
- [ROADMAP.md](ROADMAP.md) defines the current phase order and acceptance gates.
- One `MVP v0.1` epic tracks progress to the closed alpha.
- A task is complete only when it is validated and merged into `main`.

## Session contract

Before writing code, define:

```text
Phase:
Task:
Why:
Done:
Out of scope:
```

If a new idea does not help the current phase reach its exit gate, add it to Later instead of switching direction.

## Branches

Use short-lived branches from current `main`:

- `feature/player-hud`
- `feature/kill-feed`
- `fix/round-detection`
- `refactor/component-styles`
- `refactor/demo-pipeline`
- `docs/mvp-roadmap`

Keep work-in-progress to one product branch. Documentation or urgent fixes may use separate small branches when they do not overlap the product change.

Do not commit unfinished experiments directly to `main`.

## Pull request flow

1. Update local `main`.
2. Create one focused branch.
3. Make one coherent change.
4. Test the affected flow.
5. Stage only intended files.
6. Commit with a clear message.
7. Open a pull request containing:
   - What changed
   - Why it changed
   - Validation
   - Known limitations
8. Review the diff.
9. Merge only after working behavior is confirmed.
10. Update the MVP epic and record exactly one next task.

## Commit messages

Prefer concise imperative messages:

```text
feat: add player HUD
feat: add synchronized kill feed
fix: calculate score from round-end ticks
refactor: split component styles
refactor: extract round parsing
docs: update alpha roadmap
```

## Refactor rules

- Separate behavior-preserving refactors from product features.
- Move one responsibility at a time.
- Preserve JSON behavior unless a versioned contract change is intentional.
- Compare control demos before and after backend refactors.
- Do not change analysis thresholds during architecture work.

## Bug priority

A bug blocks the current phase when it:

- crashes the supported flow;
- corrupts match facts or score;
- breaks Timeline/Radar synchronization;
- prevents the phase exit gate.

Cosmetic problems, optimization and rare unsupported edge cases are tracked for their later phase unless they block testing.

## Stability and privacy

- Keep `main` runnable.
- Do not commit `.dem` files, generated JSON/reports, real SteamIDs, secrets or local environments.
- Do not rename JSON fields without updating their contract and consumers.
- Add a regression test or documented manual case for every important bug.
- Keep known-good demos outside Git and record only anonymous expected results.
- Uploaded alpha demos must have an explicit cleanup policy.

## Progress tracking

Primary progress metric:

> Percentage of the current phase acceptance criteria verified in `main`.

Supporting signals:

- focused PRs merged per week;
- demos completing the full pipeline;
- findings with valid evidence ticks;
- manual steps between upload and report;
- time from upload to ready report.

Hours spent and number of lines changed are not progress metrics.

## Near-term ownership

- Backend and analysis: Marko
- Frontend implementation and design handoff: Kirill or the project owner
- One person owns final UI decisions
- Data contracts and page structure are stabilized before major design polish
- AI consumes structured verified findings; it never becomes the source of match facts
