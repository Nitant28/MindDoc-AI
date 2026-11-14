## What and why
<!-- One paragraph: the change and the reason for it. Link the roadmap item or ADR. -->

## How it was verified
<!-- Commands you ran and their results (tests, benchmarks scored, browser checks). No unverified claims. -->
- [ ] `python -m pytest -q` (SQLite)
- [ ] `TEST_DB=postgres python -m pytest -q` (if the schema, tenancy or queries changed)
- [ ] Frontend: type-check, lint, build (if the UI changed)
- [ ] Alembic upgrade and downgrade (if there is a migration)

## Checklist
- [ ] Docs updated (`docs/IMPLEMENTATION_STATUS.md`, plus the ADR or API contract if behaviour changed)
- [ ] No secrets, customer data or fabricated numbers
- [ ] No new AGPL, GPL or non-commercial dependency
