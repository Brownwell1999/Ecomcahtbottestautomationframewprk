# Ecomchatboattestautomation

Test automation framework for ShopBot (pytest + DeepEval).

## Running the tests

ShopBot must be running locally (`docker compose up -d` in the ShopBot repo), and `.env` must contain
`ANTHROPIC_API_KEY` (copy `.env.example` to `.env`).

The suite needs **two commands**, because one kind of metric reads a trace that only exists under
`deepeval test run`:

```bash
# 1. Everything that runs under plain pytest
pytest tests -v

# 2. Trace-based tests (skipped by the command above)
deepeval test run tests/AGENTIC/test_step_efficiency.py -d all
```

Running only `pytest tests` reports `test_step_efficiency.py` as SKIPPED, so step efficiency is
not covered until you also run command 2.

Test files whose names don't start with `test_` are not collected by `pytest tests`; run them by path,
for example `pytest tests/Multi_Turn/Conversation.py -v -s`.

## Reports

Every pytest run writes two files into `reports/` (set in `pytest.ini`; the folder is git-ignored):

| File | For | What it shows |
|---|---|---|
| `reports/report.html` | People: open it in a browser | Pass/fail per test, duration, and what each test printed (metric score and the judge's reason) |
| `reports/junit.xml` | CI (Azure DevOps "Publish Test Results") | The same results in the standard JUnit format, for the pipeline's Tests tab and history |

Don't add `-s`: it stops pytest capturing the prints, so the scores and reasons would be missing from
both reports. The prints still show in the terminal without it.

A report for one group only: `pytest -m agentic --html=reports/agentic.html`.

## Thresholds (quality gates)

Every pass mark is in one file, `thresholds.yaml`, at the project root:

- `metrics`: the pass mark (0 to 1) of each judge metric. A test passes when its score is at or above it.
  The name is the metric function without `_metric` (`answer_relevancy` -> `answer_relevancy_metric()`).
- `limits`: plain limits for the tests that need no judge (answer length, response time, Top-K rank).

To tune a gate, change the number in `thresholds.yaml`; no test or framework code needs editing.
A single test can still override it: `answer_relevancy_metric(threshold=0.9)`.

## Online evaluation (scoring real conversations)

The tests in `tests/` are **offline** evaluation: we send our own questions before a release.
`online_eval/` is **online** evaluation: it scores conversations that already happened.

```bash
python -m online_eval.run_online_eval
```

What it does:

1. Reads ShopBot's recent conversation turns from LangSmith (the `shopbot-turn` traces).
2. Takes a random sample and scores each turn with the **same metric functions the tests use**.
   Real traffic has no golden answer, so only these are used: Answer Relevancy, Toxicity, PII Leakage,
   and for turns that retrieved chunks also Faithfulness and Contextual Relevancy.
3. Writes each score back onto its trace in LangSmith (feedback keys `deepeval_<metric>`), so LangSmith's
   dashboards and alerts can use them.
4. Saves `reports/online_eval.json` and compares each metric's pass rate with the gate.

Exit code: `0` = every pass rate is at or above its minimum, `1` = the gate failed (the alert),
`2` = a key is missing. Run it on a schedule and a failing run is the notification.

Settings are in the `online` section of `thresholds.yaml` (sample size, look-back window, minimum pass rates).
Each sampled turn costs judge calls (up to 5 metrics), so keep `sample_size` small.

ShopBot does not need to be running: the job needs only `LANGSMITH_API_KEY` and `ANTHROPIC_API_KEY` in `.env`.
LangSmith is only the source of traces and the place for dashboards and alerts; all scoring is DeepEval.

## Dataset management (goldens)

A golden is a test question, usually with its correct answer. They live in `test_data/`.

**Version.** `test_data/dataset_version.yaml` holds the dataset version and a history of changes. Every pytest
run shows it (terminal header, the Environment table of `report.html`, a property in `junit.xml`), so two
runs can be compared fairly: same version and a lower score means ShopBot got worse. Whenever goldens are
added or changed, raise the version and add a history line.

**Synthetic goldens.** An LLM writes questions and expected answers from ShopBot's knowledge base:

```bash
python -m dataset_tools.generate_synthetic_goldens --count 5
```

It appends to `test_data/synthetic/policy_goldens.json` with `status: "needs_review"`, one knowledge base
section per golden, and never rewrites existing entries. It uses the LLM only when you run it (about 2-3
calls per golden). Review every generated golden before a test uses it.

**Production failures.** Real failures become candidates for new goldens:

```bash
python -m dataset_tools.export_production_failures
```

It collects thumbs-down answers from ShopBot's database and failed turns from `reports/online_eval.json`
into `test_data/review/production_failures.json`. It uses no LLM. A candidate only shows the wrong answer:
write the correct `expected_output`, move it into a golden file, and raise the dataset version.

## Judge calibration (can the judge be trusted?)

Every evaluation test trusts the judge LLM, but the judge can be wrong. This script compares the judge's
verdicts with verdicts a person gave on the same answers:

```bash
python -m judge_calibration.run_calibration
```

- Labels: `test_data/calibration/judge_labels.json`. Each example has an answer, the metric, and a
  `human_verdict` of `pass` or `fail`. Each metric needs both good and bad answers.
- It runs the same metric functions the tests use, then reports the agreement per metric and how the judge
  disagreed: **too strict** (failed a good answer) or **too lenient** (passed a bad one, the dangerous kind).
- Exit code `1` when a metric's agreement is below `calibration.min_agreement` in `thresholds.yaml`.
- Report: `reports/judge_calibration.json`, which records the judge model.

Run it when the judge model changes, when a metric's instructions change, or before changing a threshold.
Labels must come from a person: set `"confirmed_by_human": true` after checking each one. The script warns
while any label is still a draft. Each labelled example costs one metric evaluation; ShopBot is not needed.
