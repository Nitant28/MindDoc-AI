"""Leave-one-source-out (LOSO) fragility of an analyst finding (R8; proposal I §2.3–2.7, design F §6).

Which sources does a finding stand or fall on? For an analyst finding the lineage is exact: it rests on specific
claim versions, and each claim on the documents it was read from. So fragility is computed exactly, without the
re-run estimator of proposal I §2.5 (that is needed only when a model sits between sources and findings).

* **Source clusters.** Documents that are copies of each other fail together, so they count as one source: two
  statements whose transaction rows are at least 90% identical (Jaccard on date, amount and direction) are joined, e.g.
  a PDF statement and an Account Aggregator import of the same account. Clusters are the connected components.
* **Facts and providers.** Each supporting claim is a fact the finding needs (a conjunction: the finding is the
  analyst's reading of all of them together). A fact is *provided* by the cluster of its own evidence and by the
  cluster of any **corroborating** claim: the other side of the same transfer recorded in the counterparty's statement
  (opposite direction, same amount and currency, dates at most 3 days apart, parties matching after entity
  resolution), or the same transfer in another statement of the same account.
* **Results.** The finding holds after removing a set of clusters T iff every fact keeps a provider outside T.
  - essential clusters: the only provider of some fact (removing one kills the finding; LOSO score 1);
  - k-fragility κ: the fewest clusters whose removal kills the finding = the smallest provider set of any fact
    (exact for a conjunction of disjunctions; `bound_type = exact`);
  - responsibility ρ(S) = max over facts provided by S of 1 / |providers| (Chockler–Halpern; 1 = essential).
* **Not measured:** whether a source is genuine; documents that support a fact without being cited (hidden
  dependence) unless they are corroborating transfer claims; non-transfer evidence. Contradicting claims are listed
  but are not part of the fragility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from typing import Optional

METHOD = "loso-exact-lineage v1"
JACCARD_COPY = 0.9
DATE_SLACK_DAYS = 3


@dataclass(frozen=True)
class ClaimFact:
    claim_id: int
    kind: str                    # TRANSFERRED_TO | RECEIVED_FROM
    amount_minor: int
    currency: str
    valid_date: Optional[date]
    document_id: Optional[int]   # the statement the claim was read from
    subject: tuple               # canonical holder of the statement account, or ("account", id)
    obj: tuple                   # canonical counterparty, or ("record", id)


@dataclass
class Result:
    method: str
    bound_type: str
    clusters: dict[str, list[int]]               # cluster label → document ids
    facts: list[dict]
    essential: list[str]
    k_fragility: Optional[int]
    loso_score: int
    responsibility: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------------------------- pure parts

def copy_clusters(doc_rows: dict[int, set]) -> dict[int, int]:
    """Union-find over documents whose row signatures overlap by at least JACCARD_COPY. Returns doc → root doc."""
    parent = {d: d for d in doc_rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    docs = sorted(doc_rows)
    for a, b in combinations(docs, 2):
        ra, rb = doc_rows[a], doc_rows[b]
        if ra and rb and len(ra & rb) / len(ra | rb) >= JACCARD_COPY:
            parent[find(b)] = find(a)
    return {d: find(d) for d in docs}


def corroborates(c: ClaimFact, other: ClaimFact) -> bool:
    """`other` records the same transfer as `c` from an independent document."""
    if other.claim_id == c.claim_id or other.document_id is None or other.document_id == c.document_id:
        return False
    if other.amount_minor != c.amount_minor or other.currency != c.currency:
        return False
    if c.valid_date is None or other.valid_date is None or abs((other.valid_date - c.valid_date).days) > DATE_SLACK_DAYS:
        return False
    if other.kind == c.kind:  # the same side, seen in another statement of the same account
        return other.subject == c.subject and other.obj == c.obj
    return other.subject == c.obj and other.obj == c.subject  # the other side of the transfer


def hitting(providers: list[frozenset]) -> tuple[Optional[int], set, dict]:
    """κ, essential providers and responsibility for a conjunction of facts, each with its set of providers."""
    if not providers or any(not p for p in providers):
        return None, set(), {}
    kappa = min(len(p) for p in providers)
    essential = {next(iter(p)) for p in providers if len(p) == 1}
    resp: dict = {}
    for p in providers:
        for s in p:
            resp[s] = max(resp.get(s, 0.0), 1.0 / len(p))
    return kappa, essential, resp


def brute_force(providers: list[frozenset]) -> tuple[Optional[int], set]:
    """Reference for tests: the smallest removal set that leaves some fact with no provider, by enumeration."""
    universe = sorted(set().union(*providers)) if providers else []
    for k in range(1, len(universe) + 1):
        for t in combinations(universe, k):
            ts = set(t)
            if any(p <= ts for p in providers):
                essential = {s for s in universe if any(p == {s} for p in providers)}
                return k, essential
    return None, set()


def analyse(support: list[ClaimFact], case_claims: list[ClaimFact], doc_rows: dict[int, set],
            statuses: Optional[dict[int, str]] = None) -> Result:
    docs = {c.document_id for c in support + case_claims if c.document_id is not None}
    root = copy_clusters({d: doc_rows.get(d, set()) for d in docs})
    members: dict[int, list[int]] = {}
    for d, r in root.items():
        members.setdefault(r, []).append(d)
    names: dict[int, str] = {}  # only the clusters this finding touches, labelled S1, S2, … in order of use

    def name(r: int) -> str:
        if r not in names:
            names[r] = f"S{len(names) + 1}"
        return names[r]

    facts, providers, notes = [], [], []
    for c in support:
        own = root.get(c.document_id)
        corr = [o for o in case_claims if corroborates(c, o) and o.document_id in root]
        prov = ({own} if own is not None else set()) | {root[o.document_id] for o in corr}
        labelled = sorted({name(r) for r in prov}, key=lambda x: int(x[1:]))
        providers.append(frozenset(labelled))
        facts.append({"claim_id": c.claim_id, "providers": labelled,
                      "own_source": name(own) if own is not None else None,
                      "corroborated_by": [{"claim_id": o.claim_id, "document_id": o.document_id,
                                           "source": name(root[o.document_id])} for o in corr],
                      "status": (statuses or {}).get(c.claim_id)})
    kappa, essential, resp = hitting(providers)
    if kappa is None:
        notes.append("a supporting claim has no source document left; the finding cannot be assessed")
    if any(f["status"] == "needs_review" for f in facts):
        notes.append("some supporting claims come from rows whose balances did not reconcile (needs review)")
    if providers and len(set().union(*providers)) == 1:
        notes.append("every supporting claim comes from one source")
    return Result(method=METHOD, bound_type="exact",
                  clusters={label: sorted(members[r]) for r, label in sorted(names.items(), key=lambda x: int(x[1][1:]))},
                  facts=facts, essential=sorted(essential, key=lambda x: int(x[1:])), k_fragility=kappa,
                  loso_score=1 if essential else 0,
                  responsibility={k: round(v, 3) for k, v in sorted(resp.items(), key=lambda x: int(x[0][1:]))},
                  notes=notes)


# ------------------------------------------------------------------------------------------------ database

def for_finding(db, case_id: int, finding_id: int) -> dict:
    """Fragility of one finding version, from the claims it pins and the case's current claims."""
    from app.database.models import (Claim, ClaimEvidence, Document, FindingSupport, PartyMention, Statement,
                                     StatementTxn)
    from app.identity.service import canonical_map

    sup_rows = db.query(FindingSupport).filter(FindingSupport.finding_id == finding_id).all()
    support_ids = [s.claim_id for s in sup_rows if s.role == "supports"]
    contradicting = [s.claim_id for s in sup_rows if s.role == "contradicts"]
    pinned = {c.id: c for c in db.query(Claim).filter(Claim.id.in_(support_ids or [-1]))}
    current = db.query(Claim).filter(Claim.case_id == case_id, Claim.superseded_at.is_(None)).all()
    cmap = canonical_map(db, case_id)

    stmt_by_doc = {s.document_id: s for s in db.query(Statement).filter(Statement.document_id.in_(
        {c.subject_document_id for c in list(pinned.values()) + current if c.subject_document_id} or {-1}))}
    holder_party: dict[int, int] = {}
    accounts = {s.bank_account_id for s in stmt_by_doc.values() if s.bank_account_id}
    for m in db.query(PartyMention).filter(PartyMention.source_type == "account_holder",
                                           PartyMention.source_id.in_(accounts or {-1})):
        if m.party_id in cmap:
            holder_party[m.source_id] = cmap[m.party_id]

    def subject_of(c) -> tuple:
        st = stmt_by_doc.get(c.subject_document_id)
        if st is not None and st.bank_account_id in holder_party:
            return ("party", holder_party[st.bank_account_id])
        return ("account", st.bank_account_id if st is not None else c.subject_document_id)

    def obj_of(c) -> tuple:
        return ("party", cmap[c.object_party_id]) if c.object_party_id in cmap else ("record", c.object_party_id)

    ev_doc = {e.claim_id: e.document_id for e in db.query(ClaimEvidence).filter(
        ClaimEvidence.claim_id.in_([c.id for c in list(pinned.values()) + current] or [-1]))}

    def fact(c) -> ClaimFact:
        return ClaimFact(c.id, c.kind, c.amount_minor, c.currency, c.valid_date,
                         ev_doc.get(c.id) or c.subject_document_id, subject_of(c), obj_of(c))

    support = [fact(pinned[i]) for i in support_ids if i in pinned]
    case_claims = [fact(c) for c in current]
    doc_ids = {f.document_id for f in support + case_claims if f.document_id}
    rows: dict[int, set] = {d: set() for d in doc_ids}
    st_doc = {s.id: s.document_id for s in stmt_by_doc.values() if s.document_id in doc_ids}
    for t in db.query(StatementTxn).filter(StatementTxn.statement_id.in_(list(st_doc) or [-1])):
        rows[st_doc[t.statement_id]].add((t.txn_date, t.debit_minor, t.credit_minor))
    names = {d.id: d.filename for d in db.query(Document).filter(Document.id.in_(doc_ids or {-1}))}
    res = analyse(support, case_claims, rows, statuses={c.id: c.status for c in pinned.values()})
    return {"method": res.method, "bound_type": res.bound_type, "k_fragility": res.k_fragility,
            "loso_score": res.loso_score, "essential_sources": res.essential,
            "responsibility": res.responsibility,
            "sources": {k: [{"document_id": d, "filename": names.get(d)} for d in v] for k, v in res.clusters.items()},
            "facts": res.facts, "contradicting_claims": contradicting, "notes": res.notes,
            "explanation": "κ is the fewest independent sources whose removal leaves a supporting claim with no "
                           "evidence. κ = 1 means the finding rests on one source (listed as essential)."}
