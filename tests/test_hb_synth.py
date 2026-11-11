"""HB-Synth v1 generator: deterministic, held-out test split, well-formed labels."""
import hashlib
import json

from benchmarks.hallucination import agreement, synth


def _digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def test_generator_is_deterministic_and_sized():
    a, b = synth.cases(), synth.cases()
    assert _digest(a) == _digest(b)
    dev, test = synth.cases("dev"), synth.cases("test")
    assert len(dev) + len(test) == len(a) >= 1000
    assert {c["label"] for c in a} == {"supported", "unsupported"}
    assert len({c["id"] for c in a}) == len(a)


def test_test_split_holds_out_families_and_names():
    dev, test = synth.cases("dev"), synth.cases("test")
    dev_fams, test_fams = {c["family"] for c in dev}, {c["family"] for c in test}
    assert {"guarantee", "fundflow", "email"} <= test_fams - dev_fams
    dev_text = " ".join(c["passage"] for c in dev)
    for name in synth.POOLS["test"]["firms"] + synth.POOLS["test"]["last"] + synth.POOLS["test"]["cities"]:
        assert name not in dev_text, name
    assert not set(synth.POOLS["dev"]["firms"]) & set(synth.POOLS["test"]["firms"])


def test_failure_classes_present_in_both_splits():
    for split in ("dev", "test"):
        tags = {c["tag"] for c in synth.cases(split)}
        assert {"converse", "table_column", "declined", "possessive", "computed_pct", "computed_total",
                "from_to", "interval"} <= tags, split


def test_formatting_helpers():
    assert synth.grouped(12400000) == "1,24,00,000"
    assert synth.amt(1240000, "lakh") == "₹12.4 lakh"
    assert synth.amt(45000000, "crore2") == "Rs 4.50 crore"
    assert not synth.representable(112500, "lakh")


def test_cohen_kappa():
    assert agreement.cohen_kappa([("supported", "supported"), ("unsupported", "unsupported")]) == 1.0
    k = agreement.cohen_kappa([("supported", "supported"), ("supported", "unsupported"),
                               ("unsupported", "unsupported"), ("unsupported", "supported")])
    assert abs(k) < 1e-9
