# EntityBench (EB) v0 — entity resolution results

`python -m benchmarks.entities.run --split {dev,test} --n 30 --report`. Thirty synthetic cases per split
(`benchmarks/entities/generator.py`; dev seeds 1000+, test seeds 9000+).

**Cases.** Each case has 18–41 parties (60% organisations) and about 80 counterparty records, as they appear across
statement narrations, invoices and KYC pages. Printed names vary in several ways:
- legal-form spelling, case, an "M/s" prefix;
- 18–30 character narration truncation, one-character typos, abbreviations;
- initials and reordered names for people.

Identifiers are sparse: PAN 10% of records, GSTIN 8%, UPI VPA 40%, account+IFSC 20%.

**Deliberate hard cases** are added to every case:
- confusable siblings ("Sunrise Traders" vs "Sunrise Trading Co");
- group companies with the same name and different legal forms ("X Ltd" vs "X LLP");
- homonyms: two different people with the same name.

**Resolver** (`app/identity/resolver.py`, model `splink-5.0.0/fs-v1`):
- Deterministic links on a validated PAN, a GSTIN's PAN, a UPI VPA or an account+IFSC.
- Hard cannot-link on different PANs, enforced at cluster level so transitive chains cannot join two PANs.
- Splink 5 (Fellegi–Sunter, DuckDB) with **fixed m/u probabilities** instead of per-case EM, because cases are too
  small for stable estimates. The priors are documented in the code and were tuned on dev only.
- Auto band:
  - an identifier-corroborated match with p ≥ 0.99; or
  - an organisation with the same normalised name and a compatible legal form, where that name does not appear with
    two different legal forms in the case.
- **People with the same name and no shared identifier always go to review.**

| Date | Split | Auto precision (95% CI) | Auto recall (95% CI) | Wrong auto pairs | **High-risk wrong** | Review: cluster pairs per case | Review true-match share | Recall if all review pairs accepted |
|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | dev (30 cases, 2,363 records) | 0.980 (0.973–0.986) | 0.573 (0.555–0.590) | 35 | **0** | 26.7 | 0.668 | 0.858 |
| 2026-11-12 | **test** (30 cases, 2,354 records; scored once) | **0.979** (0.971–0.985) | 0.578 (0.560–0.596) | 36 | **0** | 28.3 | 0.687 | 0.870 |

A *high-risk* wrong merge joins records of two true parties that both carry a PAN or GSTIN somewhere in the case.

**Against the R5 acceptance criteria (roadmap J).**
- **Met:** zero high-risk wrong merges.
- **Borderline:** auto precision is 0.980 on dev and 0.979 on test, against a target of ≥ 0.98.
- **Not met:** auto recall is 0.58, against a target of ≥ 0.90. The gap is mostly a deliberate policy:
  - Same-name people never auto-merge. Allowing it (`person_exact_auto=True`) raised dev recall to 0.784, but
    precision fell to 0.931 and **22 high-risk wrong merges** appeared.
  - The benchmark injects homonyms far more often than a single real engagement would, so it is adversarial on purpose.
  - The rest of the gap is typos, initials and truncation, which go to review rather than auto-merge.

**What changed during development (dev only).**

| Run | Auto precision | Auto recall | Notes |
|---|---|---|---|
| 1 | 0.971 | 0.229 | 59.5 review pairs per case |
| 2 | 0.942 | 0.61 | 8 high-risk wrong pairs |
| 3 | 0.981 | 0.566 | 0 high-risk; final, with review threshold 0.3 |

Run 1 to run 2 made three changes:
- **Generator fix:** VPAs were not unique. A VPA belongs to one account holder, so two parties sharing one was a
  generator artefact.
- **Corroboration:** a VPA's *local part* stopped counting as corroboration, because "rekha@…" on two different PSPs
  had merged two different people.
- **Name comparison:** canonical abbreviations, plus truncation-prefix, token-order and initial+surname levels.

Run 2 to run 3 made two changes:
- **Generator fix:** no more accidental same-name organisations. Deliberate group companies were added instead.
- **Group-company rule:** a name printed with two legal forms in one case auto-links only between identical explicit
  forms. Form-less mentions of that name go to review.

**Not shown.**
- No real counterparty data has been processed.
- The generator and the resolver were written by the same developer.
- Narration extraction (`app/identity/narration.py`) is measured only indirectly, through the API test on generated
  statements.
- About 0.5 s per case with about 80 records; larger cases are not yet measured.
