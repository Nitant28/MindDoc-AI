# Security policy

## Reporting a vulnerability
Do not open a public issue. Use GitHub's private vulnerability reporting (**Security → Report a vulnerability** on
this repository). If that option is not shown, contact the maintainer privately through their GitHub profile.

Include the affected version or commit, the steps to reproduce and the impact. You will get an acknowledgement, and
fixes are released with a note in the status log.

Please do not test against other people's data. The public demo holds only synthetic data and is reset on every
deploy.

## How MindDoc protects data
- **Tenant isolation in the database:** every tenant table is under `FORCE ROW LEVEL SECURITY`. The application
  connects as a non-owner role and sets the tenant per transaction.
- **Case-level access:** inside an organisation, only members of a case can see its documents, findings and reports.
  Non-members get 404.
- **Append-only records:** the application role cannot rewrite identity events, findings, frozen reports, disclosure
  copies or the audit trail.
- **Account numbers:** only the last four digits are stored, plus a keyed hash for matching.
- **Disclosure copies:** third parties' personal data is withheld, with a reason recorded for each item.
- **Credentials:** passwords use PBKDF2 (310,000 iterations). Invitation tokens are stored only as SHA-256 hashes.
  Authentication endpoints are rate-limited.

Known limitations are listed in `docs/PROJECT_CONTEXT.md` (section "Known limitations"), for example that stored
documents are not redacted at rest.
