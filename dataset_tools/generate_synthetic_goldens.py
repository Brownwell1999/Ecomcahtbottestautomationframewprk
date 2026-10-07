"""Generate synthetic goldens (question + expected answer) from ShopBot's knowledge base.

Synthetic = written by an LLM instead of typed by a person. The LLM reads one section of a policy
document and writes a question a customer could ask about it, plus the correct answer.

Flow:  knowledge base .md files -> split into "## " sections -> pick sections not used yet
       -> DeepEval Synthesizer (LLM) writes one golden per section
       -> append to test_data/synthetic/policy_goldens.json with status "needs_review"

Every generated golden must be REVIEWED by a person before a test trusts it: the LLM can write a
silly question or a wrong answer. Change "needs_review" to "approved" (or delete the entry) after checking.

Run:  python -m dataset_tools.generate_synthetic_goldens --count 5
Needs: ANTHROPIC_API_KEY in .env (the LLM), and ShopBot's repo on this machine (the knowledge base files).
Cost: about 2-3 LLM calls per golden, only when you run this script (never during a test run).
"""

import argparse
import json
import sys

from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import EvolutionConfig

from framework.metrics.chatbot_metrics import judge_llm
from framework.utils.config import KNOWLEDGE_BASE_DIR, TEST_DATA_DIR

OUTPUT_FILE = TEST_DATA_DIR / "synthetic" / "policy_goldens.json"

# trade_in_policy.md is wrong ON PURPOSE (negative-test data in ShopBot), so it must not become a golden
EXCLUDED_FILES = {"trade_in_policy.md"}


def read_sections():
    """Split every policy file into its "## " sections.
    Returns a list of {"source_file", "section", "text"}, where text = the heading and its lines."""
    sections = []
    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        if path.name in EXCLUDED_FILES:
            continue
        current = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                current = {"source_file": path.name, "section": line[3:].strip(), "text": line}
                sections.append(current)
            elif current is not None:
                current["text"] += "\n" + line
    return sections


def pick_sections(sections, already_used, count):
    """Choose `count` sections that have no golden yet, taking one from each file in turn,
    so a small number of goldens still covers every document."""
    by_file = {}
    for section in sections:
        if (section["source_file"], section["section"]) not in already_used:
            by_file.setdefault(section["source_file"], []).append(section)

    picked = []
    while len(picked) < count and any(by_file.values()):
        for file_sections in by_file.values():
            if file_sections and len(picked) < count:
                picked.append(file_sections.pop(0))
    return picked


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic goldens from ShopBot's knowledge base.")
    parser.add_argument("--count", type=int, default=5, help="how many goldens to generate (default 5)")
    count = parser.parse_args().count

    # 1. Goldens we already have (kept as they are), and the sections they came from
    existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8")) if OUTPUT_FILE.exists() else []
    already_used = {(golden["source_file"], golden["section"]) for golden in existing}

    # 2. Choose the sections to write goldens for
    picked = pick_sections(read_sections(), already_used, count)
    if not picked:
        print("Every knowledge base section already has a golden: nothing to generate.")
        return 0
    print(f"Generating {len(picked)} goldens from:")
    for section in picked:
        print(f"  {section['source_file']} > {section['section']}")

    # 3. The LLM writes one question + expected answer per section.
    #    num_evolutions=0: plain questions, no extra rewriting steps (fewest LLM calls)
    model = judge_llm()
    # ponytail: DeepEval has no price list entry for this Claude model, so its cost comes back as None
    # and the Synthesizer crashes adding None to its cost counter. Report 0 instead. Remove this when
    # DeepEval knows the model's price (the cost counter is not used by this script).
    price_lookup = model.calculate_cost
    model.calculate_cost = lambda input_tokens, output_tokens: price_lookup(input_tokens, output_tokens) or 0.0

    synthesizer = Synthesizer(model=model, async_mode=False,
                              evolution_config=EvolutionConfig(num_evolutions=0))
    new_goldens = []
    for section in picked:
        goldens = synthesizer.generate_goldens_from_contexts(
            contexts=[[section["text"]]], include_expected_output=True, max_goldens_per_context=1)
        for golden in goldens:
            new_goldens.append({
                "input": golden.input,
                "expected_output": golden.expected_output,
                "context": [section["text"]],
                "source_file": section["source_file"],
                "section": section["section"],
                "status": "needs_review",     # a person checks it, then changes this to "approved"
            })

    # 4. Append to the file (existing goldens are never rewritten)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(existing + new_goldens, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAdded {len(new_goldens)} goldens. {OUTPUT_FILE} now has {len(existing) + len(new_goldens)}.")
    print('Review each one, then change its status from "needs_review" to "approved".')
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
