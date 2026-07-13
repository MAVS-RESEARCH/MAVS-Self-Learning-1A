"""Explicit Phase 1 domain adapters for the fixed-representation gauntlet."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phase1DomainAdapter:
    """Declares the visible contract used to compile one domain family."""

    domain: str
    base_log_odds: float
    opportunity_kind: str
    evidence_semantics: str
    action_namespace: str


DOMAIN_ADAPTERS: dict[str, Phase1DomainAdapter] = {
    "text_safety": Phase1DomainAdapter("text_safety", -1.45, "text_response", "policy and content-risk evidence", "respond_or_abstain"),
    "tool_use": Phase1DomainAdapter("tool_use", -1.20, "tool_invocation", "permission, argument, and side-effect evidence", "execute_or_block"),
    "cyber_triage": Phase1DomainAdapter("cyber_triage", -1.00, "cyber_alert", "observable alert and exposure evidence", "triage_or_escalate"),
    "medical_triage_proxy": Phase1DomainAdapter("medical_triage_proxy", -1.10, "medical_proxy_case", "non-clinical synthetic urgency evidence", "route_or_escalate"),
    "financial_approval_proxy": Phase1DomainAdapter("financial_approval_proxy", -1.35, "financial_proxy_case", "synthetic approval and anomaly evidence", "approve_or_review"),
    "multi_agent_operations": Phase1DomainAdapter("multi_agent_operations", -0.90, "delegated_operation", "delegation, dependency, and consensus evidence", "delegate_or_veto"),
    "synthetic_control": Phase1DomainAdapter("synthetic_control", -1.25, "control_state", "bounded synthetic process evidence", "act_or_hold"),
    "retrieval_qa": Phase1DomainAdapter("retrieval_qa", -1.55, "retrieval_answer", "support, provenance, and contradiction evidence", "answer_or_abstain"),
}


def get_domain_adapter(domain: str) -> Phase1DomainAdapter:
    """Return the approved adapter and fail closed on undeclared domains."""

    try:
        return DOMAIN_ADAPTERS[domain]
    except KeyError as error:
        raise ValueError(f"No approved Phase 1 adapter for domain: {domain}") from error
