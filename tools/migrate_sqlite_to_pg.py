"""Copy an existing MindDoc SQLite database into PostgreSQL (one-time, non-destructive to the source).

    python tools/migrate_sqlite_to_pg.py --sqlite ./minddoc.db --postgres postgresql+pg8000://user:pw@host/db

* Runs Alembic to head on the target first; refuses to run if the target already has documents (no silent merge).
* Copies tenants and users, then every tenant's rows inside a transaction whose `app.tenant_id` is that tenant, so the
  row-level-security WITH CHECK policies validate every inserted row.
* Child rows that had no tenant_id in SQLite (chunks, chat sessions/messages, saved items, mentions) inherit it from
  their parent; rows whose parent tenant cannot be determined are reported and skipped, never guessed.
* Legacy v1 users in the shared "default" tenant stay there (quarantine is an owner decision, docs/OWNER_ACTIONS.md).
* Verifies per-table row counts, then resets id sequences. The SQLite file is opened read-only.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from sqlalchemy import MetaData, Table, create_engine, select, text

ORDER = ["tenants", "users", "documents", "document_chunks", "entities", "entity_mentions", "relations",
         "chat_sessions", "chat_messages", "saved_items", "query_logs", "cases", "case_documents", "statements",
         "statement_txns", "reconciliation_checks", "audit_events"]
NO_RLS = {"tenants", "users"}
ROLE = "minddoc_app"  # created by migration 0002


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True)
    ap.add_argument("--postgres", required=True)
    a = ap.parse_args()

    import os
    os.environ["DATABASE_URL"] = a.postgres
    from app.database.migrate import upgrade_head
    upgrade_head(a.postgres)

    src = create_engine(f"sqlite:///file:{a.sqlite}?mode=ro&uri=true")
    dst = create_engine(a.postgres)
    smeta, dmeta = MetaData(), MetaData()
    smeta.reflect(src)
    dmeta.reflect(dst)
    with dst.connect() as c:
        c.execute(text("SELECT set_config('app.tenant_id', '-1', false)"))  # owner sees nothing under FORCE RLS
        if c.execute(text("SELECT count(*) FROM tenants")).scalar():
            print("target already has data; refusing to merge. Use an empty database.", file=sys.stderr)
            return 2

    with src.connect() as s:
        rows = {t: [dict(r._mapping) for r in s.execute(select(smeta.tables[t]))] for t in ORDER if t in smeta.tables}

    doc_tenant = {r["id"]: r["tenant_id"] for r in rows.get("documents", [])}
    user_tenant = {r["id"]: r["tenant_id"] for r in rows.get("users", [])}
    session_tenant = {r["id"]: user_tenant.get(r.get("user_id")) for r in rows.get("chat_sessions", [])}
    parent = {"document_chunks": lambda r: doc_tenant.get(r.get("document_id")),
              "entity_mentions": lambda r: doc_tenant.get(r.get("document_id")),
              "chat_sessions": lambda r: user_tenant.get(r.get("user_id")),
              "chat_messages": lambda r: session_tenant.get(r.get("session_id")),
              "saved_items": lambda r: user_tenant.get(r.get("user_id"))}

    skipped = defaultdict(int)
    by_tenant: dict[str, dict] = {t: defaultdict(list) for t in ORDER}
    for t, rs in rows.items():
        cols = {c.name for c in dmeta.tables[t].columns}
        for r in rs:
            r = {k: v for k, v in r.items() if k in cols}
            if t not in NO_RLS:
                if r.get("tenant_id") is None and t in parent:
                    r["tenant_id"] = parent[t](r)
                if r.get("tenant_id") is None:
                    skipped[t] += 1
                    continue
            by_tenant[t][r.get("tenant_id") if t not in NO_RLS else None].append(r)

    with dst.begin() as c:  # non-RLS tables first
        for t in ("tenants", "users"):
            for r in by_tenant[t][None]:
                c.execute(dmeta.tables[t].insert().values(**r))
    tenants = sorted({tid for t in ORDER if t not in NO_RLS for tid in by_tenant[t]})
    for tid in tenants:
        with dst.begin() as c:
            c.execute(text(f'SET LOCAL ROLE "{ROLE}"'))  # RLS applies even if the login is a superuser
            c.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tid)})
            for t in ORDER:
                if t in NO_RLS:
                    continue
                for r in by_tenant[t].get(tid, []):
                    c.execute(dmeta.tables[t].insert().values(**r))

    ok = True
    for t in ORDER:
        if t not in rows:
            continue
        expected = len(rows[t]) - skipped[t]
        got = 0
        if t in NO_RLS:
            with dst.connect() as c:
                got = c.execute(text(f"SELECT count(*) FROM {t}")).scalar()
        else:
            for tid in tenants:  # count as each tenant: proves the rows are visible to their own tenant
                with dst.begin() as c:
                    c.execute(text(f'SET LOCAL ROLE "{ROLE}"'))
                    c.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tid)})
                    got += c.execute(text(f"SELECT count(*) FROM {t}")).scalar()
        flag = "ok" if got == expected else "MISMATCH"
        ok &= got == expected
        print(f"{t:18s} source {len(rows[t]):6d}  copied {got:6d}  skipped {skipped[t]:4d}  {flag}")
    with dst.begin() as c:  # max ids come from the source: under FORCE RLS the owner cannot see all rows
        for t in ORDER:
            if t in rows and rows[t] and "id" in dmeta.tables[t].columns and t != "case_documents":
                top = max(r["id"] for r in rows[t] if r.get("id") is not None)
                c.execute(text(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), :m)"), {"m": top})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
