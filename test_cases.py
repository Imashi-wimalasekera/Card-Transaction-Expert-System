"""
TEST CASES

"""

from inference_engine import run_inference, explain

BASE = dict(
    card_status="active", card_expired=False, suspected_fraud=False,
    card_present=True, pin_required=True, pin_tries_remaining=3, pin_correct=True,
    merchant_allowed=True, function_supported=True, terminal_permitted=True,
    response_timeout=False, amount=5000, available_balance=50000,
)

CASES = [
    {"name": "TC1 - Straightforward approved purchase",
     "facts": dict(BASE, txn_type="purchase"),
     "expected": "00"},

    {"name": "TC2 - Lost card presented",
     "facts": dict(BASE, txn_type="purchase", card_status="lost"),
     "expected": "41"},

    {"name": "TC3 - Stolen card presented",
     "facts": dict(BASE, txn_type="purchase", card_status="stolen"),
     "expected": "43"},

    {"name": "TC4 - Blocked/restricted card",
     "facts": dict(BASE, txn_type="purchase", card_status="blocked"),
     "expected": "62"},

    {"name": "TC5 - Expired card",
     "facts": dict(BASE, txn_type="purchase", card_expired=True),
     "expected": "54"},

    {"name": "TC6 - Fraud engine flagged the transaction",
     "facts": dict(BASE, txn_type="purchase", suspected_fraud=True),
     "expected": "59"},

    {"name": "TC7 - PIN tries exhausted",
     "facts": dict(BASE, txn_type="purchase", pin_tries_remaining=0),
     "expected": "75"},

    {"name": "TC8 - Incorrect PIN entered (tries remaining)",
     "facts": dict(BASE, txn_type="purchase", pin_correct=False),
     "expected": "55"},

    {"name": "TC9 - Card-not-present, CVV mismatch",
     "facts": dict(BASE, txn_type="purchase", card_present=False, cvv_match=False,
                   pin_required=False),
     "expected": "05"},

    {"name": "TC10 - Merchant category restricted",
     "facts": dict(BASE, txn_type="purchase", merchant_allowed=False),
     "expected": "03"},

    {"name": "TC11 - Insufficient funds",
     "facts": dict(BASE, txn_type="purchase", amount=80000, available_balance=50000),
     "expected": "51"},

    {"name": "TC12 - ATM withdrawal exceeds daily amount limit",
     "facts": dict(BASE, txn_type="withdrawal", amount=40000, available_balance=100000,
                   daily_withdrawn=30000, daily_limit=50000, daily_count=1, max_daily_count=4),
     "expected": "61"},

    {"name": "TC13 - ATM withdrawal exceeds daily count limit",
     "facts": dict(BASE, txn_type="withdrawal", amount=5000, available_balance=100000,
                   daily_withdrawn=5000, daily_limit=100000, daily_count=4, max_daily_count=4),
     "expected": "65"},

    {"name": "TC14 - Valid ATM withdrawal within all limits",
     "facts": dict(BASE, txn_type="withdrawal", amount=10000, available_balance=100000,
                   daily_withdrawn=5000, daily_limit=100000, daily_count=1, max_daily_count=4),
     "expected": "00"},
]


def run_all():
    passed = 0
    for case in CASES:
        facts = dict(case["facts"])
        run_inference(facts)
        actual = facts.get("code")
        ok = actual == case["expected"]
        passed += ok
        print(f"{case['name']}")
        print(f"  expected={case['expected']}  actual={actual}  {'PASS' if ok else 'FAIL'}")
        print(f"  {facts.get('message')}")
        print()

    print(f"{passed}/{len(CASES)} test cases passed.")


if __name__ == "__main__":
    run_all()
