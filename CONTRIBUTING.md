# Contributing to MindDoc AI

MindDoc produces evidence that people defend in front of committees and courts. The engineering rules follow from
that.

## Ground rules
- **Never fabricate a result.** A number in a doc, README or UI comes from a committed benchmark report or a live
  API, never from a mock-up.
- **Benchmarks are pre-registered.** Commit the generator, splits, metrics and acceptance criteria first. Tune on the
  dev split only, then score the held-out split once with `--final` from a clean tree. Report misses as misses.
- **No verdicts.** Detectors, findings and reports describe patterns and evidence. They never label fraud or intent.
- **Exact money.** Amounts are integer paise (`app/finance/money.py`); CI rejects floats in the finance code.
- **Provenance is not optional.** Anything derived from a document keeps its page, region and source SHA-256.
- **Licence-clean.** No AGPL, GPL or non-commercial components in the shipped image; the slim build stays torch-free.
- **Secrets stay out of git.** Use `.env` (see `.env.example`); never paste connection strings or tokens in issues.

## Workflow
1. Branch from `consolidate/v2-base`. `main` is production and changes only with the owner's approval.
2. Keep commits small and logical: code, tests and docs together, with the verification you actually ran.
3. Run the checks:
   ```bash
   python -m pytest -q                         # SQLite, offline
   TEST_DB=postgres python -m pytest -q        # PostgreSQL with row-level security
   cd frontend && npx tsc --noEmit -p . && npx eslint src && npm run build
   ```
4. Schema changes go through an Alembic migration that upgrades and downgrades cleanly. New tenant tables get
   `FORCE ROW LEVEL SECURITY` (the RLS test fails otherwise).
5. Update `docs/IMPLEMENTATION_STATUS.md` with what was built and how it was verified.

## Where things live
- `docs/PROJECT_CONTEXT.md`: the full picture, built versus planned.
- `docs/adr/`: architecture decisions.
- `docs/review/`: design reviews and the roadmap (`J_ROADMAP.md`).
- `benchmarks/`: every generator, runner and report.
