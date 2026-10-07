# Ecomchatboattestautomation

Test automation framework for ShopBot (pytest + DeepEval).

## Running the tests

ShopBot must be running locally (`docker compose up -d` in the ShopBot repo), and `.env` must contain
`JUDGE_API_KEY` (copy `.env.example` to `.env`).

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
