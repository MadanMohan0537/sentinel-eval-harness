# Sentinel Eval Harness

[![Evaluation gate](https://github.com/MadanMohan0537/sentinel-eval-harness/actions/workflows/evaluation-gate.yml/badge.svg)](https://github.com/MadanMohan0537/sentinel-eval-harness/actions/workflows/evaluation-gate.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)

**Sentinel is a production-oriented evaluation and release-gating system for LLM and agent applications.** It turns a versioned test suite into reproducible evidence that a new prompt, model, retrieval strategy, or agent implementation is ready to release.

It is not a wrapper around a single model call. Sentinel combines case-level scoring, adversarial mutations, experiment history, statistical uncertainty, operational budgets, and CI enforcement in one inspectable system.

```bash
sentinel-eval run datasets/product_support.jsonl --mutations --min-pass-rate 0.80
```

```json
{
  "cases": 8,
  "passed": 8,
  "pass_rate": 1.0,
  "pass_rate_ci95": [1.0, 1.0],
  "total_cost_usd": 0.0,
  "gate": {"passed": true, "reasons": []}
}
```

## The product in one minute

| Stage | What Sentinel does | Why it matters |
| --- | --- | --- |
| Define | Stores expected behavior as version-controlled JSONL cases | Product requirements become testable contracts |
| Stress | Generates case-noise and context-distractor variants | Golden examples alone do not measure robustness |
| Execute | Runs model or agent calls concurrently through adapters | The target system remains vendor-independent |
| Score | Applies deterministic, quality, safety, and operational checks | A single aggregate metric cannot describe production quality |
| Quantify | Calculates seeded bootstrap confidence intervals | Teams see uncertainty, not just a misleading point estimate |
| Decide | Compares results with thresholds and the previous run | Regressions become explicit release decisions |
| Preserve | Stores run and case evidence in SQLite | Failures remain inspectable after CI completes |
| Communicate | Exposes experiment history through an API and dashboard | Product and engineering teams share the same evidence |

## The problem

Generative systems are non-deterministic. A seemingly harmless change can improve average answer quality while silently breaking a high-risk segment, increasing latency, or weakening refusal behavior. Conventional unit tests cannot express all of those conditions, while manual spot checks cannot reliably detect regressions.

Sentinel addresses four practical questions:

1. Did the candidate system satisfy the product's behavioral requirements?
2. Did it remain stable when the input or context changed slightly?
3. Did quality improve without unacceptable latency, cost, or safety regressions?
4. Is there enough evidence to allow the candidate into production?

Modern evaluation platforms converge on datasets built from curated examples and production traces, multiple evaluator types, experiment comparison, trace evaluation, and continuous monitoring. Sentinel implements the engineering core of that workflow as a portable repository that can run without paid evaluation infrastructure.

## Core capabilities

- **Reproducible datasets:** JSONL suites are validated, deduplicated by case ID, and content-addressed with a stable fingerprint.
- **Composite evaluation:** exact-match, required-term, refusal, latency, grounding, and reference-quality scorers run together.
- **Robustness probes:** deterministic input-noise and context-distractor mutations test invariance beyond the golden set.
- **Statistical evidence:** pass rates include a seeded 95% bootstrap confidence interval rather than presenting a point estimate alone.
- **Release gates:** CI fails when absolute quality falls below policy or when quality regresses beyond an allowed delta.
- **Failure isolation:** an endpoint failure is recorded on its case instead of destroying the entire experiment.
- **Operational metrics:** latency, token usage, and cost fields live beside quality metrics.
- **Trace-ready records:** adapters return structured execution events for agent-step and tool-use analysis.
- **Experiment ledger:** SQLite stores immutable run summaries and case-level evidence.
- **Zero-cost mode:** the deterministic fixture adapter exercises the entire platform in local development and CI.
- **Real-model mode:** an OpenAI-compatible HTTP adapter can evaluate hosted or local models without coupling the harness to one vendor.
- **Quality dashboard:** the included FastAPI application exposes run history and a responsive experiment view.

## Evaluation dimensions

| Scorer | Signal | Typical use |
| --- | --- | --- |
| `exact_match` | Normalized equality with a reference answer | Classification, extraction, structured answers |
| `required_terms` | Coverage of contractually required concepts | Product policy and support responses |
| `refusal_safety` | Correct refusal behavior on safety-tagged cases | Access control and harmful requests |
| `latency_budget` | Response time against a case-level budget | User experience and operational SLOs |
| `groundedness` | Output-token support from supplied context | RAG and knowledge assistants |
| `reference_f1` | Precision/recall overlap with a reference response | Offline semantic-quality proxy |

The offline scorers are deliberately transparent. They provide deterministic CI coverage and can be supplemented with an LLM judge when the evaluation requires nuance.

## Architecture

```mermaid
flowchart TD
    A[Versioned JSONL suite] --> B[Validation and fingerprint]
    B --> C[Robustness mutations]
    C --> D[Concurrent model adapter]
    D --> E[Composite scorer registry]
    E --> F[Bootstrap confidence interval]
    F --> G{Release policy}
    G -->|Pass| H[Deployable candidate]
    G -->|Block| I[Case-level evidence]
    E --> J[(SQLite experiment ledger)]
    J --> K[API and dashboard]
```

## Repository map

```text
src/eval_harness/
├── adapters/          # Fixture and OpenAI-compatible HTTP targets
├── scorers/           # Deterministic and offline quality scorers
├── api.py             # Run-history API and dashboard server
├── cli.py             # Evaluation command line interface
├── dataset.py         # Validation and dataset fingerprinting
├── models.py          # Typed evaluation contracts
├── mutations.py       # Adversarial robustness probes
├── runner.py          # Concurrent execution and release policy
├── statistics.py      # Seeded bootstrap intervals
└── storage.py         # SQLite experiment ledger
datasets/              # Version-controlled golden suites
dashboard/             # Dependency-free quality dashboard
tests/                 # Unit and integration tests
.github/workflows/     # Pull-request evaluation gate
```

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
sentinel-eval run datasets/product_support.jsonl --mutations
```

The command writes a full report to `artifacts/latest-run.json`, persists the experiment in `.sentinel/runs.db`, prints the release decision, and exits with code `2` when the gate fails.

Start the local dashboard:

```bash
uvicorn eval_harness.api:app --reload
```

Open `http://localhost:8000`.

## Evaluate a real model or agent endpoint

Sentinel accepts any OpenAI-compatible chat-completions endpoint:

```bash
export MODEL_ENDPOINT="https://your-endpoint.example/v1/chat/completions"
export MODEL_NAME="candidate-model"
export MODEL_API_KEY="your-key"

sentinel-eval run datasets/product_support.jsonl \
  --adapter http \
  --mutations \
  --min-pass-rate 0.90
```

Credentials are read only from the environment and are never stored in reports or the experiment database.

### Adapter contract

New providers implement one asynchronous method:

```python
class ModelAdapter(Protocol):
    name: str

    async def generate(self, case: EvalCase) -> ModelResponse: ...
```

`ModelResponse` carries text, latency, token counts, cost, and structured trace events. This keeps scoring independent from inference and provides a clean extension point for tool-using agents.

## Dataset contract

Each JSONL row describes one behavior the system must preserve:

```json
{
  "id": "billing-001",
  "input": "When will the annual plan refund arrive?",
  "expected": "Annual plan refunds arrive within 5 to 10 business days.",
  "context": ["Approved annual plan refunds arrive within 5 to 10 business days."],
  "tags": ["support", "billing"],
  "metadata": {
    "required_terms": ["5 to 10 business days"],
    "latency_budget_ms": 3000
  }
}
```

Production suites should combine:

1. Manually curated contractual behavior
2. Anonymized high-value production traces
3. Previously observed failures
4. Safety and policy boundary cases
5. Segment-specific edge cases
6. Synthetic variants reviewed by a human

## Release policy

The default example gate requires:

- At least an 80% total pass rate
- No more than a 2 percentage-point regression against the latest stored run
- All case-specific scorer thresholds to pass

Because aggregate quality can hide important failures, a production extension should add tag-level policies such as `safety = 100%` and minimum sample sizes for each product segment.

### Gate logic

```text
candidate pass rate >= absolute threshold
AND
baseline pass rate - candidate pass rate <= allowed regression
```

A gate failure returns a non-zero process exit code, so the same policy works locally, in GitHub Actions, and in deployment pipelines.

## CI behavior

Every pull request:

1. Lints the codebase
2. Runs the test suite with coverage
3. Executes the evaluation dataset with robustness mutations
4. Applies the release threshold
5. Uploads the complete evaluation report as an artifact, even on failure

This makes AI behavior part of the same review boundary as application code.

## Deployment

The included container runs an evaluation during image build and starts the FastAPI dashboard in production mode.

```bash
docker build -t sentinel-eval .
docker run --rm -p 8000:8000 sentinel-eval
```

It can be deployed to any container host. Persist `.sentinel/runs.db` on a volume for durable experiment history. For a multi-instance deployment, replace the SQLite store with Postgres while preserving the `RunStore` interface.

## Example use cases

- Compare two model versions before changing a production endpoint
- Prevent a prompt edit from weakening safety refusals
- Test whether a RAG response remains grounded in retrieved context
- Convert a production incident into a permanent regression case
- Enforce response-time requirements for user-facing AI features
- Attach machine-readable evaluation evidence to every pull request

## Current boundaries

Sentinel is an evaluation foundation, not a hosted observability service. The current release uses SQLite, provides offline proxy metrics instead of a calibrated hosted judge, and includes deterministic mutations rather than a generative red-team agent. Those boundaries keep the repository inexpensive and reproducible; the roadmap describes the production extensions.

## Roadmap

- Calibrated LLM-as-judge scorer with blinded pairwise comparisons
- Human-review queue for low-confidence and evaluator-disagreement cases
- Agent goal-plan-action and tool-trajectory scorers
- Retrieval attribution and citation-entailment checks
- Slice metrics and drift alerts by tag, model, tenant, and prompt version
- OpenTelemetry trace ingestion
- Evaluation budget scheduler for production sampling
- Postgres-backed multi-user control plane

## Evaluation principles used

- Prefer task-specific tests over broad academic benchmarks.
- Combine deterministic checks with model-based judgment instead of trusting either alone.
- Preserve individual failures and segment labels, not only averages.
- Evaluate robustness, latency, and cost alongside response quality.
- Treat previously observed failures as permanent regression cases.
- Keep datasets, thresholds, and reports versionable and reviewable.

## Design references

- [OpenAI evaluation best practices](https://platform.openai.com/docs/guides/evals)
- [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [MLflow production trace evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/)
- [DeepEval](https://github.com/confident-ai/deepeval)

## License

MIT
