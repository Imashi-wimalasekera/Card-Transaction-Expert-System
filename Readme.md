# Card Transaction Authorization Advisor — Expert System

Decides APPROVE/DECLINE for a card transaction (POS purchase or ATM withdrawal) and returns the applicable ISO 8583 (field 39) response code, using a forward-chaining inference engine in plain Python (no external libraries).

## Domain and knowledge source

Domain: card transaction authorization / decline-code determination.

Knowledge sources:
- [S1] myPOS Developer Docs - ISO 8583 field 39 response code table
- [S2] softwareag forum - VISA Base I ISO 8583 response code list
- [S3] CCBill KB - Comprehensive List of Credit Card Decline Codes

Rules R1-R17 map directly onto standard, published ISO 8583 response codes (41 lost card, 43 stolen card, 62 restricted card, 54 expired card, 59 suspected fraud, 75 PIN tries exceeded, 55 incorrect PIN, 05 do not honor, 03 invalid merchant, 13 invalid amount, 12 invalid transaction, 61 exceeds withdrawal amount limit, 65 exceeds withdrawal count limit, 51 insufficient funds, 40 function not supported, 58 not permitted to terminal, 68 response too late). 

Rules R18-R20 are this project's own combination/reporting logic (decide APPROVE when nothing else matched, tag a risk tier, compile the final message) and are labelled as such, not as card-scheme citations.

## How to run it locally 

Requirements: Python 3.8+, no installation needed (standard library only).

```
cd card_expert_system
python3 interface.py        # interactive CLI - enter one transaction's details
python3 test_cases.py       # runs 14 pre-built test cases automatically
```

## Architecture

- **Knowledge base** (`knowledge_base.py`) - 20 IF-THEN rules with sources.
- **Working memory** - the `facts` dict: transaction facts in, derived conclusions (code,reason, message, decision, risk_tier) out.
- **Inference engine** (`inference_engine.py`) - forward-chaining match-fire loop
- **Explanation facility** - every fired rule is logged to a trace (`explain()`), so the interface shows *why* a decision was made.
- **User interface** (`interface.py`) - CLI collecting transaction facts and printing the decision + explanation trace.

## Files

```
knowledge_base.py     20 rules + citations
inference_engine.py   forward-chaining engine + explanation trace
interface.py          interactive CLI
test_cases.py         14 automated test cases
```

