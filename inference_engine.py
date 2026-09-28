"""
INFERENCE ENGINE
================
A simple forward-chaining ("data-driven") inference engine, shared by the
card-authorization knowledge base.

Match-fire cycle:
1. Working memory starts holding only the FACTS supplied by the interface (the transaction's details).
2. Each cycle, the engine scans every rule in order. A rule "fires" if its condition is true and it hasn't already fired; firing runs its action, which writes new facts into working memory.
3. This repeats until a full cycle produces no new facts, or max_cycles is reached.
4. The current cycle number is written to facts["_cycle"] before each pass, which R18 (the "approve if nothing else matched" rule) uses to make sure every decline rule has had a chance to fire before an approval is recorded.
5. Every fired rule is appended to an explanation trace for transparency.

"""

from knowledge_base import ALL_RULES


def run_inference(facts, rules=None, max_cycles=10):
    rules = rules if rules is not None else ALL_RULES
    facts.setdefault("_fired", set())
    facts.setdefault("_trace", [])

    for cycle in range(max_cycles):
        facts["_cycle"] = cycle
        fired_this_cycle = False
        for rule in rules:
            if rule.try_fire(facts):
                fired_this_cycle = True
        if not fired_this_cycle:
            break

    return facts


def explain(facts):
    lines = []
    for rule in facts.get("_trace", []):
        lines.append(f"  [{rule.id}] {rule.description}\n        source: {rule.source}")
    return "\n".join(lines)
