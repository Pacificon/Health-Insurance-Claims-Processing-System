from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings
from app.models.claims import ClaimSubmission
from app.models.trace import DecisionTrace, StageStatus
from app.orchestrator.graph import ClaimsOrchestrator
from app.services.policy_loader import PolicyLoader


CaseCheck = Callable[[DecisionTrace], tuple[bool, str]]


@dataclass
class CaseResult:
    case_id: str
    case_name: str
    passed: bool
    checks: list[dict[str, str]]
    trace: dict[str, Any]


def _stage(trace: DecisionTrace, name: str):
    for stage in trace.stages:
        if stage.stage == name:
            return stage
    raise KeyError(f"Stage '{name}' not found in trace for {trace.claim_id}")


def _contains_all(text: str | None, *needles: str) -> bool:
    haystack = (text or "").lower()
    return all(needle.lower() in haystack for needle in needles)


def _currency_mentions(text: str | None, *amounts: int) -> bool:
    haystack = (text or "").replace(",", "")
    return all(
        any(variant in haystack for variant in [str(amount), f"₹{amount}", f"Rs. {amount}", f"INR {amount}"])
        for amount in amounts
    )


def _check(description: str, passed: bool) -> tuple[bool, str]:
    return passed, description


def _build_checks() -> dict[str, list[tuple[str, CaseCheck]]]:
    return {
        "TC001": [
            ("Stops before making a decision", lambda t: _check("decision is null", t.decision is None)),
            (
                "Documents stage fails and extraction is skipped",
                lambda t: _check(
                    "document validation failed and extraction skipped",
                    _stage(t, "DOCUMENT_VALIDATION").status == StageStatus.FAILED
                    and _stage(t, "EXTRACTION").status == StageStatus.SKIPPED,
                ),
            ),
            (
                "Message names uploaded and required document types",
                lambda t: _check(
                    "message names PRESCRIPTION and HOSPITAL_BILL",
                    _contains_all(t.user_message, "prescription", "hospital_bill"),
                ),
            ),
        ],
        "TC002": [
            ("Stops before making a decision", lambda t: _check("decision is null", t.decision is None)),
            (
                "Message identifies the unreadable file and asks for re-upload",
                lambda t: _check(
                    "message names blurry_bill.jpg and asks to re-upload",
                    _contains_all(t.user_message, "blurry_bill.jpg", "re-upload"),
                ),
            ),
        ],
        "TC003": [
            ("Stops before making a decision", lambda t: _check("decision is null", t.decision is None)),
            (
                "Message includes the two mismatched patient names",
                lambda t: _check(
                    "message names Rajesh Kumar and Arjun Mehta",
                    _contains_all(t.user_message, "rajesh kumar", "arjun mehta"),
                ),
            ),
        ],
        "TC004": [
            ("Approves the claim", lambda t: _check("decision is APPROVED", str(t.decision) == "APPROVED")),
            ("Approves 1350", lambda t: _check("approved amount is 1350", t.approved_amount == 1350)),
            (
                "Confidence is above 0.85",
                lambda t: _check("confidence score is above 0.85", (t.confidence_score or 0) > 0.85),
            ),
        ],
        "TC005": [
            ("Rejects the claim", lambda t: _check("decision is REJECTED", str(t.decision) == "REJECTED")),
            (
                "Rejects for waiting period",
                lambda t: _check("WAITING_PERIOD is in rejection reasons", "WAITING_PERIOD" in t.rejection_reasons),
            ),
            (
                "Message states the eligibility date",
                lambda t: _check(
                    "message includes 2024-11-30",
                    _contains_all(t.user_message, "2024-11-30"),
                ),
            ),
        ],
        "TC006": [
            ("Returns partial approval", lambda t: _check("decision is PARTIAL", str(t.decision) == "PARTIAL")),
            ("Approves 8000", lambda t: _check("approved amount is 8000", t.approved_amount == 8000)),
            (
                "Line-item output captures the cosmetic exclusion",
                lambda t: _check(
                    "line item decisions mention whitening rejection",
                    any(
                        "whitening" in json.dumps(item).lower()
                        and item.get("approved") is False
                        and "excluded" in (item.get("reason") or "").lower()
                        for item in (t.line_item_decisions or [])
                    ),
                ),
            ),
        ],
        "TC007": [
            ("Rejects the claim", lambda t: _check("decision is REJECTED", str(t.decision) == "REJECTED")),
            (
                "Rejects for missing pre-auth",
                lambda t: _check("PRE_AUTH_MISSING is in rejection reasons", "PRE_AUTH_MISSING" in t.rejection_reasons),
            ),
            (
                "Message explains pre-auth and resubmission guidance",
                lambda t: _check(
                    "message mentions pre-authorization and resubmit",
                    _contains_all(t.user_message, "pre-auth", "resubmit"),
                ),
            ),
        ],
        "TC008": [
            ("Rejects the claim", lambda t: _check("decision is REJECTED", str(t.decision) == "REJECTED")),
            (
                "Rejects for per-claim limit",
                lambda t: _check("PER_CLAIM_EXCEEDED is in rejection reasons", "PER_CLAIM_EXCEEDED" in t.rejection_reasons),
            ),
            (
                "Message states both the limit and claimed amount",
                lambda t: _check(
                    "message includes 5000 and 7500",
                    _currency_mentions(t.user_message, 5000, 7500),
                ),
            ),
        ],
        "TC009": [
            (
                "Routes to manual review",
                lambda t: _check("decision is MANUAL_REVIEW", str(t.decision) == "MANUAL_REVIEW"),
            ),
            (
                "Fraud signals include same-day count and prior claim IDs",
                lambda t: _check(
                    "fraud signal includes count 4 and CLM_0081-0083",
                    bool(t.fraud_signals)
                    and t.fraud_signals[0].get("same_day_count") == 4
                    and all(claim_id in t.fraud_signals[0].get("claim_ids", []) for claim_id in ["CLM_0081", "CLM_0082", "CLM_0083"]),
                ),
            ),
        ],
        "TC010": [
            ("Approves the claim", lambda t: _check("decision is APPROVED", str(t.decision) == "APPROVED")),
            ("Approves 3240", lambda t: _check("approved amount is 3240", t.approved_amount == 3240)),
            (
                "Financial breakdown shows discount before co-pay",
                lambda t: _check(
                    "breakdown shows 4500 -> 3600 -> 3240",
                    bool(t.financial_breakdown)
                    and t.financial_breakdown.get("eligible_base") == 4500
                    and t.financial_breakdown.get("amount_after_network_discount") == 3600
                    and t.financial_breakdown.get("approved_amount") == 3240,
                ),
            ),
        ],
        "TC011": [
            ("Still produces a decision", lambda t: _check("decision is APPROVED", str(t.decision) == "APPROVED")),
            (
                "Marks the component failure",
                lambda t: _check("FraudAgent appears in components_failed", "FraudAgent" in t.components_failed),
            ),
            (
                "Recommends manual review with reduced confidence",
                lambda t: _check(
                    "manual review recommended and confidence below 0.85",
                    t.manual_review_recommended and (t.confidence_score or 1) < 0.85,
                ),
            ),
        ],
        "TC012": [
            ("Rejects the claim", lambda t: _check("decision is REJECTED", str(t.decision) == "REJECTED")),
            (
                "Rejects for excluded condition",
                lambda t: _check("EXCLUDED_CONDITION is in rejection reasons", "EXCLUDED_CONDITION" in t.rejection_reasons),
            ),
            (
                "Confidence is above 0.90",
                lambda t: _check("confidence score is above 0.90", (t.confidence_score or 0) > 0.90),
            ),
        ],
    }


def evaluate_cases(case_ids: list[str] | None = None) -> list[CaseResult]:
    cases = json.loads((ROOT / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    if case_ids:
        selected = {case_id.upper() for case_id in case_ids}
        cases = [case for case in cases if case["case_id"] in selected]
        missing = selected - {case["case_id"] for case in cases}
        if missing:
            raise ValueError(f"Unknown case id(s): {', '.join(sorted(missing))}")

    policy = PolicyLoader(ROOT / "policy_terms.json").load()
    orchestrator = ClaimsOrchestrator(policy, Settings())
    checks_by_case = _build_checks()

    results: list[CaseResult] = []
    for case in cases:
        submission = ClaimSubmission.model_validate(case["input"])
        trace = orchestrator.process_claim(submission)
        case_checks: list[dict[str, str]] = []
        passed = True
        for label, evaluator in checks_by_case[case["case_id"]]:
            ok, detail = evaluator(trace)
            passed = passed and ok
            case_checks.append(
                {
                    "label": label,
                    "status": "PASS" if ok else "FAIL",
                    "detail": detail,
                }
            )
        results.append(
            CaseResult(
                case_id=case["case_id"],
                case_name=case["case_name"],
                passed=passed,
                checks=case_checks,
                trace=trace.model_dump(mode="json"),
            )
        )
    return results


def write_report(results: list[CaseResult], *, report_path: Path | None = None) -> Path:
    report_path = report_path or (ROOT / "eval_report.md")
    passed_count = sum(1 for result in results if result.passed)
    total = len(results)

    lines = [
        "# Evaluation Report",
        "",
        f"Overall score: **{passed_count}/{total}**",
        "",
        "| Case | Result |",
        "|------|--------|",
    ]
    lines.extend(
        f"| {result.case_id} | {'PASS' if result.passed else 'FAIL'} |"
        for result in results
    )

    for result in results:
        lines.extend(
            [
                "",
                f"## {result.case_id} — {result.case_name}",
                "",
                f"Result: **{'PASS' if result.passed else 'FAIL'}**",
                "",
                "| Check | Status | Detail |",
                "|-------|--------|--------|",
            ]
        )
        lines.extend(
            f"| {check['label']} | {check['status']} | {check['detail']} |"
            for check in result.checks
        )
        lines.extend(
            [
                "",
                "Decision output:",
                "",
                "```json",
                json.dumps(result.trace, indent=2),
                "```",
            ]
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Plum assignment test cases through the claims pipeline and write eval_report.md.",
    )
    parser.add_argument(
        "--case",
        action="append",
        metavar="TC00X",
        help="Run only the given case id (repeatable), e.g. --case TC004",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "eval_report.md",
        help="Output markdown report path (default: repo-root eval_report.md)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        results = evaluate_cases(args.case)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    report_path = write_report(results, report_path=args.report)
    passed_count = sum(1 for result in results if result.passed)
    total = len(results)

    print(f"Wrote {report_path}")
    print(f"Score: {passed_count}/{total}")
    for result in results:
        print(f"{result.case_id}: {'PASS' if result.passed else 'FAIL'}")

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
