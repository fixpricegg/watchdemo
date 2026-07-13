# Development Workflow

## Branches

- `main` contains the latest stable version.
- New work is done in short-lived branches.
- Use names such as:
  - `feature/bomb-tracking`
  - `feature/grenade-events`
  - `fix/timeline-score`
  - `refactor/demo-script`

Do not commit unfinished experiments directly to `main`.

## Task format

Every task should define:

1. Current project phase
2. Why the task matters
3. Files likely to change
4. Definition of done
5. What is explicitly out of scope

Example:

```text
Task: Bomb tracking
Phase: Radar v1
Value: Show the main objective state during a round
Done:
- carrier visible
- dropped bomb visible
- planted bomb visible
- defuse/explosion state visible
- synchronized with Timeline
Out of scope:
- final visual design
- AI commentary
```

## Pull request flow

1. Create a branch from `main`.
2. Make one coherent change.
3. Test the affected flow locally.
4. Commit with a clear message.
5. Open a pull request.
6. Review the diff and known risks.
7. Merge into `main` only when the working behavior is confirmed.

## Commit messages

Prefer concise imperative messages:

```text
feat: add bomb carrier tracking
fix: calculate score from round-end ticks
refactor: split round parsing from report generation
docs: update radar roadmap
```

## Stability rules

- Do not commit `.dem` files, generated reports, secrets, or local environments.
- Keep `main` runnable.
- Do not rename JSON fields without updating documentation and frontend usage.
- Add a regression test or manual test case for every important bug.
- Preserve one known-good demo for local verification, but keep the file outside Git.

## Near-term ownership

- Backend and analysis: Marko
- Frontend implementation and design handoff: Kirill
- Data contracts must be frozen before major UI polish begins.
