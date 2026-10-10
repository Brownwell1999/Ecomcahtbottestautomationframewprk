# Ecomchatboattestautomation

Test automation framework for ShopBot (pytest + DeepEval).

How it works and why (strategy, design, architecture, flow charts): [docs/FRAMEWORK_GUIDE.md](docs/FRAMEWORK_GUIDE.md).

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

## CI

There are two pipeline files. Only the first one runs.

| File | Status | What it does |
|---|---|---|
| `azure-pipelines.yml` | Active | On a push to `main`: deploy ShopBot, wait until it answers, smoke test, publish results. No judge calls |
| `azure-pipelines.quality-gates.yml` | Designed, **not connected** (it never runs) | Five quality gates on every pull request that block the merge |

The quality-gates pipeline is kept ready and switched off for now, because two of its gates cost judge LLM calls.
What it does once connected:

- **A pull request into `main`** runs all five gates. With the branch protection rule on GitHub switched on,
  the PR cannot be merged until they are green. Draft PRs do not start the pipeline.
- **A push to `main`** (the merge) runs Gate 1 only (no judge calls).
- **A run started by hand** (Azure DevOps: Pipelines > Run pipeline) runs all five gates.

A gate that fails turns the pipeline red and the later gates do not run.

| Gate | Rule | Command | Judge calls |
|---|---|---|---|
| 1. Smoke | Every smoke test must pass | `pytest -m smoke` | None |
| 2. AI evaluation | Answer Relevancy and Faithfulness at or above their pass mark (0.7) | `pytest tests/CHATBOT/test_answer_relevancy.py tests/PROMPT/test_Faithfulness.py` | 6 tests |
| 3. Security | Every security test must pass (prompt injection, PII leakage, toxicity, unsafe action) | `pytest tests/SECURITY_GUARDRAILS` | 12 tests |
| 4. Performance | One answer, and the p95 of 5 answers, within 30 seconds; bad requests get a clear error | `pytest tests/PERFORMANCE/test_response_time.py tests/PERFORMANCE/test_reliability_and_error_handling.py` | None |
| 5. Regression | No Gate 2 metric drops by more than 0.10 against `baseline/baseline.json` | `python -m baseline.compare_with_baseline` | None |

- The pass marks and the allowed drop come from `thresholds.yaml`; nothing is hard-coded in the pipeline.
- Each gate writes its own report (`reports/junit_gate<N>_*.xml`, `reports/report_gate<N>_*.html`) and its own
  score file, named by the environment variable `RUN_SCORES_FILE` (default `run_scores.json`). Gate 5 reads the
  score file Gate 2 wrote.
- The baseline holds Answer Relevancy 1.0 and Faithfulness 1.0 (measured, three cases each), so Gate 5 fails when
  either average is below 0.9. After a run you are happy with, update it with
  `python -m baseline.compare_with_baseline --accept` and commit `baseline/baseline.json`.
- The pipeline needs the secret variable `ANTHROPIC_API_KEY` and fails with a clear message when it is missing.
- To switch it on: create a pipeline in Azure DevOps from `azure-pipelines.quality-gates.yml`, then follow the
  checklist in section 9.4 of the guide (branch protection on GitHub is what blocks the merge).

More detail and flow charts: sections 9.3 and 9.4 of [docs/FRAMEWORK_GUIDE.md](docs/FRAMEWORK_GUIDE.md).
The CI/CD architecture (roles, pull requests, DEV, QA and PROD): [docs/CICD_ARCHITECTURE.md](docs/CICD_ARCHITECTURE.md).

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

Agent-mode turns (`shopbot-agent` traces) are sampled too (`online.agent_sample_size`) and judged with Task
Completion. Their tool calls are read from the steps inside the trace, so this works in production, where
the dev-only `debug` field that the pytest tests read (`debug.toolCalls`, `debug.retrievalContext`) is off.

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

## Baseline comparison (better or worse than before?)

A fixed threshold only says a score is acceptable: a drop from 0.95 to 0.72 still passes. The baseline
comparison compares the last run with a version you accepted earlier.

1. Every pytest run that measures a metric writes `reports/run_scores.json`: the average score per metric,
   labelled with the prompt version and models ShopBot reported, the judge model and the dataset version.
2. Compare it with the stored baseline:

```bash
python -m baseline.compare_with_baseline
```

   Each metric is `SAME`, `IMPROVED`, `REGRESSION` or new. A change only counts when it is larger than
   `baseline.max_score_drop` in `thresholds.yaml` (LLM scores wobble between runs). Exit code `1` on a regression.
3. When you are happy with a run, make it the new baseline and commit `baseline/baseline.json`:

```bash
python -m baseline.compare_with_baseline --accept
```

The baseline is kept per metric, so a run of a few tests updates only the metrics it measured. The comparison
uses no LLM. It warns when the judge model or the dataset version differs, because scores measured with a
different judge or different goldens are not comparable. Tests that use DeepEval's `assert_test` or the
prompt injection classifier are not recorded yet.

## Red teaming (generated attacks)

The security tests replay a fixed list of attacks. The red team script has an LLM write **new** attacks in
different disguises and runs them against ShopBot:

```bash
python -m redteam.run_redteam
```

1. One LLM call writes the attacks (default 5), starting from the seed attacks in
   `test_data/security/prompt_injection.json`. Each uses a different disguise: rephrasing, role-play,
   a hypothetical, hidden in a normal request, fake authority, another language.
2. Each attack is sent to ShopBot and the judge labels the reply `resisted`, `partially_followed` or
   `followed_injection`.
3. Everything is saved to `reports/redteam.json` (attack, reply, label, reason), so a finding can be reproduced.
4. Exit code `1` when the resistance rate is below `redteam.min_resistance_rate` in `thresholds.yaml`.
5. Attacks that worked go to `test_data/review/redteam_findings.json`. After a person confirms one, add it to
   `test_data/security/prompt_injection.json` and raise the dataset version.

Cost: 1 LLM call to write the attacks and 1 judge call per attack. ShopBot must be running.

This is a small home-made generator for one weakness (prompt injection), not a full red-teaming tool: it has
no multi-turn or adaptive attacks. A dedicated tool such as DeepTeam would be the next step; it needs
Python below 3.14, so it would run in its own environment. Only use this against your own ShopBot.
