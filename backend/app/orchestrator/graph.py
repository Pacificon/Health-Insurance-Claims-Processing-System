import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.decision_synthesizer import DecisionSynthesizer
from app.agents.document_validator import DocumentValidator
from app.agents.extraction_agent import ExtractionAgent
from app.agents.fraud_agent import FraudResult, FraudSignalAgent
from app.config import Settings
from app.engine.financial import FinancialCalculator
from app.engine.policy_engine import PolicyEngine
from app.models.claims import ClaimSubmission, Decision
from app.models.policy import Member, PolicyTerms
from app.models.trace import DecisionTrace, StageStatus, StageTrace


class ClaimGraphState(TypedDict, total=False):
    claim_id: str
    submission: ClaimSubmission
    file_contents: dict[str, bytes]
    member: Member
    doc_validation: Any
    extraction: Any
    policy_result: Any
    financial_result: Any
    fraud_result: FraudResult | None
    components_failed: list[str]
    early_stop: bool
    trace: DecisionTrace


class ClaimsOrchestrator:
    def __init__(self, policy: PolicyTerms, settings: Settings) -> None:
        self._policy = policy
        self._settings = settings
        self._doc_validator = DocumentValidator(policy)
        self._extraction_agent = ExtractionAgent(settings)
        self._policy_engine = PolicyEngine(policy)
        self._financial_calculator = FinancialCalculator(policy)
        self._fraud_agent = FraudSignalAgent(policy)
        self._synthesizer = DecisionSynthesizer()
        self._graph = self._build_graph()

    def process_claim(
        self,
        submission: ClaimSubmission,
        *,
        claim_id: str | None = None,
        file_contents: dict[str, bytes] | None = None,
    ) -> DecisionTrace:
        initial: ClaimGraphState = {
            "claim_id": claim_id or f"CLM_{uuid.uuid4().hex[:8].upper()}",
            "submission": submission,
            "file_contents": file_contents or {},
            "components_failed": [],
            "early_stop": False,
        }
        final_state = self._graph.invoke(initial)
        return final_state["trace"]

    def _build_graph(self):
        graph = StateGraph(ClaimGraphState)
        graph.add_node("intake", self._intake_node)
        graph.add_node("document_validation", self._document_validation_node)
        graph.add_node("finalize_early_stop", self._finalize_early_stop_node)
        graph.add_node("extraction", self._extraction_node)
        graph.add_node("policy", self._policy_node)
        graph.add_node("financial", self._financial_node)
        graph.add_node("fraud", self._fraud_node)
        graph.add_node("synthesize", self._synthesize_node)

        graph.set_entry_point("intake")
        graph.add_edge("intake", "document_validation")
        graph.add_conditional_edges(
            "document_validation",
            self._route_after_document_validation,
            {"stop": "finalize_early_stop", "continue": "extraction"},
        )
        graph.add_edge("finalize_early_stop", END)
        graph.add_edge("extraction", "policy")
        graph.add_edge("policy", "financial")
        graph.add_edge("financial", "fraud")
        graph.add_edge("fraud", "synthesize")
        graph.add_edge("synthesize", END)
        return graph.compile()

    def _intake_node(self, state: ClaimGraphState) -> ClaimGraphState:
        submission = state["submission"]
        member = self._policy.get_member(submission.member_id)
        if member is None:
            raise ValueError(f"Member '{submission.member_id}' not found in policy.")
        if submission.policy_id != self._policy.policy_id:
            raise ValueError(
                f"Policy ID mismatch: submission has '{submission.policy_id}', "
                f"expected '{self._policy.policy_id}'."
            )
        return {"member": member}

    def _document_validation_node(self, state: ClaimGraphState) -> ClaimGraphState:
        result = self._doc_validator.validate(state["submission"])
        return {
            "doc_validation": result,
            "early_stop": not result.passed,
        }

    @staticmethod
    def _route_after_document_validation(state: ClaimGraphState) -> str:
        if state.get("early_stop"):
            return "stop"
        return "continue"

    def _finalize_early_stop_node(self, state: ClaimGraphState) -> ClaimGraphState:
        doc_validation = state["doc_validation"]
        synthesized = self._synthesizer.synthesize(
            doc_validation=doc_validation,
            early_stop=True,
        )
        trace = DecisionTrace(
            claim_id=state["claim_id"],
            stages=[
                StageTrace(
                    stage="DOCUMENT_VALIDATION",
                    status=StageStatus.FAILED,
                    checks=doc_validation.checks,
                    messages=doc_validation.messages,
                ),
                StageTrace(stage="EXTRACTION", status=StageStatus.SKIPPED),
                StageTrace(stage="POLICY", status=StageStatus.SKIPPED),
                StageTrace(stage="FINANCIAL", status=StageStatus.SKIPPED),
                StageTrace(stage="FRAUD", status=StageStatus.SKIPPED),
            ],
            decision=None,
            user_message=synthesized.user_message,
            confidence_score=synthesized.confidence_score,
        )
        return {"trace": trace}

    def _extraction_node(self, state: ClaimGraphState) -> ClaimGraphState:
        result = self._extraction_agent.extract(
            state["submission"],
            file_contents=state.get("file_contents"),
            force_eval_bypass=_all_docs_have_content(state["submission"]),
        )
        return {"extraction": result}

    def _policy_node(self, state: ClaimGraphState) -> ClaimGraphState:
        result = self._policy_engine.evaluate(
            state["submission"],
            state["member"],
            state["extraction"].extracted,
        )
        return {"policy_result": result}

    def _financial_node(self, state: ClaimGraphState) -> ClaimGraphState:
        policy_result = state["policy_result"]
        if policy_result.decision == Decision.REJECTED:
            return {"financial_result": None}

        extracted = state["extraction"].extracted
        hospital_name = extracted.hospital_name if extracted else None
        result = self._financial_calculator.calculate(
            state["submission"],
            eligible_amount=policy_result.eligible_amount,
            hospital_name=hospital_name or state["submission"].hospital_name,
        )
        return {"financial_result": result}

    def _fraud_node(self, state: ClaimGraphState) -> ClaimGraphState:
        components_failed = list(state.get("components_failed", []))
        submission = state["submission"]

        if submission.simulate_component_failure:
            components_failed.append(FraudSignalAgent.COMPONENT_NAME)
            return {
                "fraud_result": FraudResult(
                    checks=[
                        {
                            "rule": "COMPONENT_FAILURE",
                            "passed": False,
                            "component": FraudSignalAgent.COMPONENT_NAME,
                            "message": "FraudAgent skipped due to simulated component failure.",
                        }
                    ]
                ),
                "components_failed": components_failed,
            }

        try:
            result = self._fraud_agent.evaluate(submission)
            return {"fraud_result": result, "components_failed": components_failed}
        except Exception as exc:
            components_failed.append(FraudSignalAgent.COMPONENT_NAME)
            return {
                "fraud_result": FraudResult(
                    checks=[
                        {
                            "rule": "COMPONENT_FAILURE",
                            "passed": False,
                            "component": FraudSignalAgent.COMPONENT_NAME,
                            "error": str(exc),
                        }
                    ]
                ),
                "components_failed": components_failed,
            }

    def _synthesize_node(self, state: ClaimGraphState) -> ClaimGraphState:
        extraction = state["extraction"]
        policy_result = state["policy_result"]
        financial_result = state.get("financial_result")
        fraud_result = state.get("fraud_result")
        components_failed = state.get("components_failed", [])

        synthesized = self._synthesizer.synthesize(
            extraction=extraction,
            policy_result=policy_result,
            financial_result=financial_result,
            fraud_result=fraud_result,
            components_failed=components_failed,
        )

        stages = [
            StageTrace(
                stage="DOCUMENT_VALIDATION",
                status=StageStatus.PASSED,
                checks=state["doc_validation"].checks,
            ),
            StageTrace(
                stage="EXTRACTION",
                status=StageStatus.PASSED if extraction.success else StageStatus.FAILED,
                checks=extraction.checks,
                fields=extraction.extracted.model_dump() if extraction.extracted else None,
            ),
            StageTrace(
                stage="POLICY",
                status=StageStatus.FAILED if policy_result.decision == Decision.REJECTED else StageStatus.PASSED,
                checks=policy_result.checks,
                rule=policy_result.rejection_reasons[0] if policy_result.rejection_reasons else None,
                detail=policy_result.user_message,
            ),
            StageTrace(
                stage="FINANCIAL",
                status=StageStatus.SKIPPED if financial_result is None else StageStatus.PASSED,
                checks=financial_result.checks if financial_result else [],
            ),
            StageTrace(
                stage="FRAUD",
                status=StageStatus.WARNING if fraud_result and fraud_result.manual_review_required else StageStatus.PASSED,
                checks=fraud_result.checks if fraud_result else [],
            ),
        ]

        fraud_signals = None
        if fraud_result and fraud_result.signals:
            fraud_signals = [signal.model_dump() for signal in fraud_result.signals]

        line_items = None
        if policy_result.line_item_decisions:
            line_items = [item.model_dump() for item in policy_result.line_item_decisions]

        trace = DecisionTrace(
            claim_id=state["claim_id"],
            stages=stages,
            decision=synthesized.decision,
            approved_amount=synthesized.approved_amount,
            rejection_reasons=synthesized.rejection_reasons,
            confidence_score=synthesized.confidence_score,
            components_failed=components_failed,
            manual_review_recommended=synthesized.manual_review_recommended,
            user_message=synthesized.user_message,
            financial_breakdown=self._synthesizer.financial_breakdown_dict(financial_result),
            line_item_decisions=line_items,
            fraud_signals=fraud_signals,
        )
        return {"trace": trace}


def _all_docs_have_content(submission: ClaimSubmission) -> bool:
    return all(doc.content is not None for doc in submission.documents)
