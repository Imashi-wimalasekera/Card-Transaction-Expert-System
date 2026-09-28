"""
USER INTERFACE (CLI)
=====================
Collects a transaction's details, hands them to the inference engine as
working-memory facts, then prints the ISO 8583 decision code, message and
the full explanation trace.

"""

from inference_engine import run_inference, explain


def ask(prompt, cast=str, default=None):
    raw = input(prompt).strip()
    if raw == "" and default is not None:
        return default
    return cast(raw)


def ask_bool(prompt, default=None):
    while True:
        raw = input(prompt + " (y/n): ").strip().lower()
        if raw == "" and default is not None:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please answer y or n.")


def collect_facts():
    print("=== Card Transaction Authorization Advisor ===\n")
    facts = {}

    status = ask("Card status [active/lost/stolen/blocked] (default active): ", str, "active").lower()
    facts["card_status"] = status
    facts["card_expired"] = ask_bool("Is the card past its expiry date?", False)
    facts["suspected_fraud"] = ask_bool("Has an upstream fraud check flagged this transaction?", False)

    facts["txn_type"] = ask("Transaction type [purchase/withdrawal]: ", str).lower()
    facts["card_present"] = ask_bool("Is the physical card present (chip/tap/swipe)?", True)

    if facts["card_present"]:
        facts["pin_required"] = ask_bool("Does this transaction require PIN entry?", True)
        if facts["pin_required"]:
            facts["pin_tries_remaining"] = ask("PIN tries remaining before this attempt: ", int)
            facts["pin_correct"] = ask_bool("Was the PIN entered correctly?", True)
    else:
        facts["cvv_match"] = ask_bool("Did the CVV match (card-not-present transaction)?", True)

    facts["merchant_allowed"] = ask_bool("Is this merchant category permitted for the card?", True)
    facts["function_supported"] = ask_bool("Does the card support this function (e.g. cash withdrawal)?", True)
    facts["terminal_permitted"] = ask_bool("Is the transaction permitted at this terminal/acquirer?", True)
    facts["response_timeout"] = ask_bool("Did the host response time out?", False)

    facts["amount"] = ask("Transaction amount: ", float)
    facts["available_balance"] = ask("Available balance/credit: ", float)

    if facts["txn_type"] == "withdrawal":
        facts["daily_withdrawn"] = ask("Amount already withdrawn today: ", float, 0.0)
        facts["daily_limit"] = ask("Daily withdrawal amount limit: ", float)
        facts["daily_count"] = ask("Number of withdrawals already made today: ", int, 0)
        facts["max_daily_count"] = ask("Maximum withdrawals allowed per day: ", int)

    return facts


def print_result(facts):
    print("\n--- Result ---")
    print(facts.get("message", "UNKNOWN - insufficient facts"))
    if facts.get("decision") == "APPROVED":
        print(f"Risk tier (system heuristic): {facts.get('risk_tier')}")

    print("\n--- Explanation trace (rules fired, in order) ---")
    print(explain(facts))


def main():
    facts = collect_facts()
    run_inference(facts)
    print_result(facts)


if __name__ == "__main__":
    main()
