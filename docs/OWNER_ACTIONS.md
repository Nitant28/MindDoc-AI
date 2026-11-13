# Owner actions (cannot be done by the engineering assistant)

Each item: why, exact steps, how we verify. Engineering continues around these; nothing below blocks R1/R2 code work
except where noted.

## 1. Live secrets and CORS on Render (security, audit A2) — do now
1. Render dashboard → service `minddoc-ai-2` → **Environment**.
2. Set `JWT_SECRET` to a random 64-hex value (e.g. run `python -c "import secrets; print(secrets.token_hex(32))"` locally).
3. Set `CORS_ORIGINS=https://minddoc-ai-2.onrender.com`.
4. Save → Render redeploys. Existing logins are invalidated once (expected).
- Verify: log in on the live site; a token signed with `supersecretkey` still returns 401 (assistant can re-check).

## 2. Old commits with personal documents (privacy, audit A1) — do now
Either:
- **Make the repository private:** GitHub → Settings → General → Danger Zone → Change visibility → Private. (Render's
  GitHub app keeps access if it was installed with access to this repo.) **or**
- **Ask GitHub Support to purge cached refs:** https://support.github.com → "Remove sensitive data". Text to send:
  > Repository Nitant28/MindDoc-AI: sensitive files were removed from all branches with git filter-repo and
  > force-pushed. Please remove cached views and the pull-request references for PR #1 (refs/pull/1/head → 53f9f2a)
  > and garbage-collect unreferenced commits, including 1c836cf3ebeee2b4d5f240e443798b18ddaadb33 and
  > 6f4a21bbabc62f8ab5ee33f2dd1d83c6bcf2ab27.
- Verify: anonymous `GET https://api.github.com/repos/Nitant28/MindDoc-AI/contents/data/uploads?ref=6f4a21bbabc62f8ab5ee33f2dd1d83c6bcf2ab27` returns 404.

## 3. Demo database (needed to deploy R2 to the demo; not needed to build or test it)
1. Create a free Neon account (https://neon.com), project region `aws-us-west-2` (Oregon, next to Render) and Postgres 18.
2. In the Neon console: SQL editor → `CREATE EXTENSION vector; CREATE EXTENSION btree_gist; CREATE EXTENSION pg_trgm;`
3. Copy the **pooled** connection string and the **direct** one.
4. Do **not** paste them into chat. Add them in Render → Environment as `DATABASE_URL` (direct) when the R2 release is
   approved for the demo.
- Production/pilot hosting (AWS Mumbai) requires an AWS account and billing: decide after pricing (ADR-0013).

## 4. Customer discovery (gate M1 by week ~6)
- Use the interview plan in `docs/review/D_MARKET_RESEARCH.md` §7: 25 interviews across forensic/CA firms, bank
  internal audit / FRM units, NBFC credit and collections, insolvency professionals, and (fallback market) internal audit
  for procure-to-pay.
- Store notes outside git if they contain personal data; put anonymised summaries in `docs/market/interviews/` (one file
  per interview: role, firm type, problem frequency, current tools, time spent, deliverable, budget owner, quotes
  paraphrased).
- Gate M1 needs ≥ 15 interviews.

## 5. Real data for StatementBench tier 3 (later, R3/R4)
- 20–50 redacted real statements from a pilot partner under a written data-processing agreement; never committed to git.

## 6. Approvals the assistant will ask for explicitly
- Merging `consolidate/v2-base` into `main` (which deploys to Render).
- Any production database migration, credential, billing, DNS or visibility change.
- The market decision at M1 and the forensic-detector validation gate M2.
- **Account Aggregator holder data (privacy decision, open).** The AA import does not read the holder profile (name,
  PAN, mobile, …). Reading only the holder name and PAN would let AA statements link to parties automatically, as PDF
  headers do. Until you decide, an analyst can set the holder by hand.
- **`ACCOUNT_HASH_KEY`** must be set (and kept) on any persistent deployment before bank statements are uploaded.
