"""
KNOWLEDGE BASE
==============
Card Transaction Authorization Advisor - Expert System

Domain: deciding whether a card transaction (POS purchase or ATM withdrawal) should be APPROVED or DECLINED, and which ISO 8583 (field 39) response code applies.

SOURCE OF DOMAIN KNOWLEDGE
---------------------------
Rules R1-R17 map directly onto standard ISO 8583 field-39 response codes used industry-wide for card authorization messaging. 
These are NOT invented rules - the code numbers and their standard meanings are taken from published references:

    [S1] myPOS Developer Docs, "229 Response Codes" (ISO 8583 field 39
         table): https://developers.mypos.com/en/doc/online_payments/v1_4/229-response-codes
    [S2] "ISO8583 Message Format Support" thread quoting the VISA Base I
         response-code list:
         https://tech.forums.softwareag.com/t/iso8583-message-format-support/155110
    [S3] CCBill Knowledge Base, "A Comprehensive List of Credit Card
         Decline Codes": https://ccbill.com/kb/?p=3602

Rules R18-R20 are SYSTEM DESIGN rules: they resolve which single code to report when a transaction could match more than one condition, and add a non-sourced reporting heuristic. 
"""

S1 = "[S1] myPOS Developer Docs - ISO 8583 field 39 response code table"
S2 = "[S2] softwareag forum - VISA Base I ISO 8583 response code list"
S3 = "[S3] CCBill KB - Comprehensive List of Credit Card Decline Codes"
SYSTEM_DESIGN = "System design rule (author's own combination/reporting logic, not a card-scheme citation)"


class Rule:
    def __init__(self, rule_id, description, condition, action, source):
        self.id = rule_id
        self.description = description
        self.condition = condition
        self.action = action
        self.source = source

    def try_fire(self, facts):
        if self.id in facts.get("_fired", set()):
            return False
        if self.condition(facts):
            self.action(facts)
            facts.setdefault("_fired", set()).add(self.id)
            facts.setdefault("_trace", []).append(self)
            return True
        return False


def has(facts, key):
    return key in facts and facts[key] is not None


def not_decided(f):
    """True while no ISO 8583 decision code has been assigned yet - used so higher-priority hard declines (lost/stolen card, fraud) are not overwritten by a lower-priority rule firing later in the same pass."""
    return "code" not in f



# R1-R3: Card status hard stops (highest priority - card scheme "pick-up" and "restricted" categories)
R1 = Rule(
    "R1", "Lost card -> pick-up, code 41",
    lambda f: not_decided(f) and f.get("card_status") == "lost",
    lambda f: f.update({"code": "41", "reason": "Pick-up card (reported lost)"}),
    S1 + " / " + S2,
)
R2 = Rule(
    "R2", "Stolen card -> pick-up, code 43",
    lambda f: not_decided(f) and f.get("card_status") == "stolen",
    lambda f: f.update({"code": "43", "reason": "Pick-up card (reported stolen)"}),
    S1 + " / " + S2,
)
R3 = Rule(
    "R3", "Blocked/restricted card -> code 62",
    lambda f: not_decided(f) and f.get("card_status") == "blocked",
    lambda f: f.update({"code": "62", "reason": "Restricted card"}),
    S1,
)


# R4: Expired card
R4 = Rule(
    "R4", "Expired card -> code 54",
    lambda f: not_decided(f) and f.get("card_expired") is True,
    lambda f: f.update({"code": "54", "reason": "Expired card"}),
    S1 + " / " + S2,
)


# R5: Suspected fraud (upstream fraud/velocity engine flag)
R5 = Rule(
    "R5", "Suspected fraud flag set -> code 59",
    lambda f: not_decided(f) and f.get("suspected_fraud") is True,
    lambda f: f.update({"code": "59", "reason": "Suspected fraud"}),
    S3,
)


# R6-R7: PIN checks
R6 = Rule(
    "R6", "PIN tries exhausted -> code 75",
    lambda f: not_decided(f) and has(f, "pin_tries_remaining") and f["pin_tries_remaining"] <= 0,
    lambda f: f.update({"code": "75", "reason": "Allowable number of PIN tries exceeded"}),
    S3,
)
R7 = Rule(
    "R7", "PIN required and incorrectly entered -> code 55",
    lambda f: (
        not_decided(f) and f.get("pin_required") is True
        and f.get("pin_correct") is False
        and has(f, "pin_tries_remaining") and f["pin_tries_remaining"] > 0
    ),
    lambda f: f.update({"code": "55", "reason": "Incorrect personal identification number"}),
    S1 + " / " + S3,
)


# R8: CVV mismatch (card-not-present transaction) - mapped to the general security-decline code 05, as used for failed verification checks

R8 = Rule(
    "R8", "CVV mismatch on card-not-present transaction -> code 05",
    lambda f: (
        not_decided(f) and f.get("card_present") is False
        and f.get("cvv_match") is False
    ),
    lambda f: f.update({"code": "05", "reason": "Do not honor (CVV verification failed)"}),
    S1,
)

# R9: Merchant category restriction
R9 = Rule(
    "R9", "Merchant category not permitted for this card -> code 03",
    lambda f: not_decided(f) and f.get("merchant_allowed") is False,
    lambda f: f.update({"code": "03", "reason": "Invalid merchant"}),
    S1,
)

# R10-R11: Message/amount validity
R10 = Rule(
    "R10", "Non-positive transaction amount -> code 13",
    lambda f: not_decided(f) and has(f, "amount") and f["amount"] <= 0,
    lambda f: f.update({"code": "13", "reason": "Invalid amount"}),
    S1 + " / " + S2,
)
R11 = Rule(
    "R11", "Unrecognised transaction type -> code 12",
    lambda f: not_decided(f) and f.get("txn_type") not in ("purchase", "withdrawal"),
    lambda f: f.update({"code": "12", "reason": "Invalid transaction"}),
    S1,
)

# R12-R13: ATM withdrawal limits
R12 = Rule(
    "R12", "Withdrawal would exceed the daily amount limit -> code 61",
    lambda f: (
        not_decided(f) and f.get("txn_type") == "withdrawal"
        and has(f, "amount") and has(f, "daily_withdrawn") and has(f, "daily_limit")
        and (f["daily_withdrawn"] + f["amount"]) > f["daily_limit"]
    ),
    lambda f: f.update({"code": "61", "reason": "Exceeds withdrawal amount limit"}),
    S1 + " / " + S3,
)
R13 = Rule(
    "R13", "Daily withdrawal count limit already reached -> code 65",
    lambda f: (
        not_decided(f) and f.get("txn_type") == "withdrawal"
        and has(f, "daily_count") and has(f, "max_daily_count")
        and f["daily_count"] >= f["max_daily_count"]
    ),
    lambda f: f.update({"code": "65", "reason": "Exceeds withdrawal count limit"}),
    S1,
)

# R14: Insufficient funds
R14 = Rule(
    "R14", "Amount exceeds available balance -> code 51",
    lambda f: (
        not_decided(f) and has(f, "amount") and has(f, "available_balance")
        and f["amount"] > f["available_balance"]
    ),
    lambda f: f.update({"code": "51", "reason": "Insufficient funds"}),
    S1 + " / " + S2,
)

# R15: Function not supported by this card product
R15 = Rule(
    "R15", "Card product does not support this function -> code 40",
    lambda f: not_decided(f) and f.get("function_supported") is False,
    lambda f: f.update({"code": "40", "reason": "Requested function not supported"}),
    S3,
)

# R16: Terminal/acquirer not permitted
R16 = Rule(
    "R16", "Terminal/acquirer not permitted for this transaction -> code 58",
    lambda f: not_decided(f) and f.get("terminal_permitted") is False,
    lambda f: f.update({"code": "58", "reason": "Transaction not permitted to acquirer/terminal"}),
    S1 + " / " + S2,
)

# R17: Response timeout
R17 = Rule(
    "R17", "Host response timed out -> code 68",
    lambda f: not_decided(f) and f.get("response_timeout") is True,
    lambda f: f.update({"code": "68", "reason": "Response received too late"}),
    S3,
)



# R18: Approve (System Design) - if no decline condition matched (lowest priority - fires only after all other rules have had a chance to fire)
R18 = Rule(
    "R18", "No decline condition matched after all checks -> approve, code 00",
    lambda f: not_decided(f),
    lambda f: f.update({"code": "00", "reason": "Approved or completed successfully"}),
    S1 + " / " + S2 + "  (combination logic: " + SYSTEM_DESIGN + ")",
)

# 
# R19: Risk-tier tag for approved transactions (System Design heuristic - NOT a card-scheme rule)
R19 = Rule(
    "R19", "On approval, tag a risk tier based on amount vs balance ratio",
    lambda f: f.get("code") == "00" and "risk_tier" not in f,
    lambda f: f.update({
        "risk_tier": (
            "low" if f.get("amount", 0) <= 0.3 * f.get("available_balance", 1)
            else "medium" if f.get("amount", 0) <= 0.7 * f.get("available_balance", 1)
            else "high"
        )
    }),
    SYSTEM_DESIGN,
)


# R20: Compile a final human-readable message (SYSTEM DESIGN combination rule that assembles code + reason into the message shown to the user)
R20 = Rule(
    "R20", "Final Decision Message: compile code + reason ->",
    lambda f: "code" in f and "message" not in f,
    lambda f: f.update({
        "message": f"ISO 8583 response {f['code']}: {f['reason']}",
        "decision": "APPROVED" if f["code"] == "00" else "DECLINED",
    }),
    SYSTEM_DESIGN,
)

ALL_RULES = [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20]
