import asyncio

from eval_harness.adapters.fixture import FixtureAdapter
from eval_harness.dataset import dataset_fingerprint, load_jsonl
from eval_harness.runner import EvalRunner, release_gate
from eval_harness.scorers.deterministic import ExactMatch, RequiredTerms


def test_dataset_is_stable_and_unique():
    cases = load_jsonl("datasets/product_support.jsonl")
    assert len(cases) == 3
    assert dataset_fingerprint(cases) == dataset_fingerprint(list(reversed(cases)))


def test_runner_passes_fixture_suite():
    cases = load_jsonl("datasets/product_support.jsonl")
    run = asyncio.run(EvalRunner(FixtureAdapter(), [ExactMatch(), RequiredTerms()]).run(cases))
    assert run["summary"]["pass_rate"] == 1.0


def test_release_gate_blocks_regression():
    baseline = {"summary": {"pass_rate": 0.95}}
    current = {"summary": {"pass_rate": 0.90}}
    passed, reasons = release_gate(current, baseline, 0.8, 0.02)
    assert not passed
    assert "regression" in reasons[0]


def test_duplicate_ids_are_rejected(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id":"x","input":"a"}\n{"id":"x","input":"b"}\n')
    try:
        load_jsonl(path)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Expected validation error")

