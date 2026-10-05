from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from src.graph.ap.nodes import (
    extract_invoice_node,
    lookup_db_node,
    match_3_way_node,
    route_ap_decision,
    validate_invoice_node,
    human_review_node,
    generate_discrepancy_notice_node,
)
from src.graph.shared.nodes.risk_assessment import risk_assessment_node
from src.grc.nodes import governance_policy_check_node, maker_checker_review_node
from src.graph.state import FinanceState


from src.finance.reconciliation import reconciliation_node

def route_governance(state: FinanceState) -> str:
    """Routes to Maker-Checker if governance policy requires it, otherwise fallback to AP routing."""
    gov = state.get("governance_status", {})
    if gov.get("requires_checker_approval"):
        return "maker_checker"
    
    decision = state.get("routing_decision")
    if decision == "HITL":
        return "generate_discrepancy"
    if decision == "APPROVE":
        return "approve"
    return "exception"

def route_maker_checker(state: FinanceState) -> str:
    """Routes Maker-Checker decision."""
    gov = state.get("governance_status", {})
    if gov.get("approval_status") == "APPROVED":
        return "approve"
    return "exception"

def route_compliance(state: FinanceState) -> str:
    """Routes to discrepancy HITL if compliance reconciliation fails, otherwise proceeds to governance."""
    is_reconciled = state.get("is_reconciled", True)
    if not is_reconciled:
        return "generate_discrepancy"
    return "governance_policy"

def build_ap_graph():
    """Assembles and compiles the Accounts Payable (AP) workflow graph."""
    builder = StateGraph(FinanceState)

    # Add nodes
    builder.add_node("extract_invoice", extract_invoice_node)
    builder.add_node("validate_invoice", validate_invoice_node)
    builder.add_node("lookup_db", lookup_db_node)
    builder.add_node("match_3_way", match_3_way_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("compliance_check", reconciliation_node)
    builder.add_node("governance_policy", governance_policy_check_node)
    builder.add_node("maker_checker", maker_checker_review_node)
    builder.add_node("generate_discrepancy", generate_discrepancy_notice_node)
    builder.add_node("human_review", human_review_node)

    # Add edges
    builder.add_edge(START, "extract_invoice")
    builder.add_edge("extract_invoice", "validate_invoice")
    builder.add_edge("validate_invoice", "lookup_db")
    builder.add_edge("lookup_db", "match_3_way")
    
    # GRC Flow
    builder.add_edge("match_3_way", "risk_assessment")
    builder.add_edge("risk_assessment", "compliance_check")
    
    builder.add_conditional_edges(
        "compliance_check",
        route_compliance,
        {
            "governance_policy": "governance_policy",
            "generate_discrepancy": "generate_discrepancy",
        }
    )

    # Conditional routing edge from governance_policy
    builder.add_conditional_edges(
        "governance_policy",
        route_governance,
        {
            "maker_checker": "maker_checker",
            "approve": END,
            "exception": END,
            "generate_discrepancy": "generate_discrepancy",
        },
    )
    
    builder.add_conditional_edges(
        "maker_checker",
        route_maker_checker,
        {
            "approve": END,
            "exception": END,
        },
    )
    
    # Path from generate_discrepancy to human_review
    builder.add_edge("generate_discrepancy", "human_review")
    # Path from human review to END
    builder.add_edge("human_review", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory, interrupt_before=["human_review", "maker_checker"])


ap_graph = build_ap_graph()
