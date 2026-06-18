# Evaluation Report

Overall score: **1/1**

| Case | Result |
|------|--------|
| TC004 | PASS |

## TC004 — Clean Consultation — Full Approval

Result: **PASS**

| Check | Status | Detail |
|-------|--------|--------|
| Approves the claim | PASS | decision is APPROVED |
| Approves 1350 | PASS | approved amount is 1350 |
| Confidence is above 0.85 | PASS | confidence score is above 0.85 |

Decision output:

```json
{
  "claim_id": "CLM_2AC5BB58",
  "stages": [
    {
      "stage": "DOCUMENT_VALIDATION",
      "status": "PASSED",
      "checks": [
        {
          "rule": "DOCUMENT_TYPES",
          "passed": true,
          "message": "All required document types are present."
        },
        {
          "rule": "DOCUMENT_QUALITY",
          "passed": true,
          "message": "All documents are readable."
        },
        {
          "rule": "PATIENT_NAME_CONSISTENCY",
          "passed": true,
          "message": "Patient names are consistent across documents."
        },
        {
          "rule": "DOCUMENT_VALIDATION",
          "passed": true,
          "message": "All document checks passed."
        }
      ],
      "fields": null,
      "rule": null,
      "detail": null,
      "messages": []
    },
    {
      "stage": "EXTRACTION",
      "status": "PASSED",
      "checks": [
        {
          "step": "EVAL_BYPASS",
          "passed": true,
          "message": "Used embedded document content as ground-truth extraction (eval mode \u2014 Gemini not called).",
          "document_count": 2
        }
      ],
      "fields": {
        "diagnosis": "Viral Fever",
        "treatment": null,
        "tests_ordered": [],
        "line_items": [
          {
            "description": "Consultation Fee",
            "amount": 1000.0
          },
          {
            "description": "CBC Test",
            "amount": 300.0
          },
          {
            "description": "Dengue NS1 Test",
            "amount": 200.0
          }
        ],
        "hospital_name": "City Clinic, Bengaluru",
        "pre_authorization_obtained": false
      },
      "rule": null,
      "detail": null,
      "messages": []
    },
    {
      "stage": "POLICY",
      "status": "PASSED",
      "checks": [
        {
          "rule": "EXCLUDED_CONDITION",
          "passed": true,
          "message": "No policy exclusions matched."
        },
        {
          "rule": "WAITING_PERIOD",
          "passed": true,
          "message": "No waiting period violations."
        },
        {
          "rule": "PRE_AUTHORIZATION",
          "passed": true,
          "message": "Pre-authorization not required."
        },
        {
          "rule": "PER_CLAIM_LIMIT",
          "passed": true,
          "limit": 5000,
          "claimed_amount": 1500.0,
          "message": "Claim amount within per-claim limit of \u20b95,000."
        },
        {
          "rule": "POLICY_CLEAR",
          "passed": true,
          "message": "All policy checks passed"
        }
      ],
      "fields": null,
      "rule": null,
      "detail": "Claim meets policy requirements.",
      "messages": []
    },
    {
      "stage": "FINANCIAL",
      "status": "PASSED",
      "checks": [
        {
          "step": "NETWORK_DISCOUNT",
          "passed": true,
          "skipped": true,
          "message": "No network hospital discount applied."
        },
        {
          "step": "COPAY",
          "passed": true,
          "rate_percent": 10.0,
          "amount_before": 1500.0,
          "deduction": 150.0,
          "amount_after": 1350.0,
          "message": "Co-pay (10%) on \u20b91,500 = \u20b9150 deducted"
        }
      ],
      "fields": null,
      "rule": null,
      "detail": null,
      "messages": []
    },
    {
      "stage": "FRAUD",
      "status": "PASSED",
      "checks": [
        {
          "rule": "SAME_DAY_CLAIMS",
          "passed": true,
          "same_day_count": 1,
          "limit": 2,
          "message": "Same-day claim count (1) within threshold."
        }
      ],
      "fields": null,
      "rule": null,
      "detail": null,
      "messages": []
    }
  ],
  "decision": "APPROVED",
  "approved_amount": 1350.0,
  "rejection_reasons": [],
  "confidence_score": 0.92,
  "components_failed": [],
  "manual_review_recommended": false,
  "user_message": "Claim meets policy requirements. Co-pay (10%) applied on \u20b91,500 = \u20b9150 deducted. Final approved amount: \u20b91,350.",
  "financial_breakdown": {
    "eligible_base": 1500.0,
    "network_discount_applied": false,
    "network_discount_percent": 0.0,
    "network_discount_amount": 0.0,
    "amount_after_network_discount": null,
    "copay_percent": 10.0,
    "copay_amount": 150.0,
    "approved_amount": 1350.0
  },
  "line_item_decisions": null,
  "fraud_signals": null
}
```
