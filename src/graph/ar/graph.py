from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from src.graph.ar.nodes import (
    calculate_aging_node,
    extract_remittance_node,
    lookup_invoices_node,
    reconcile_payment_node,
    route_ar_decision,
    ar_human_review_node,
    generate_overdue_reminder_node,
)
from src.graph.shared.nodes.risk_assessment import risk_assessment_node
from src.grc.nodes import ar_governance_policy_check_node, ar_maker_checker_review_node
from src.graph.state import FinanceState


def route_ar_governance(state: FinanceState) -> str:
    """Routes to Maker-Checker if governance policy requires it, otherwise fallback to AR decision routing."""
    gov = state.get("governance_status", {})
    if gov.get("requires_checker_approval"):
        return "maker_checker"
    
    decision = state.get("routing_decision")
    if decision == "HITL":
        return "hitl"
    elif decision == "OVERDUE":
        return "overdue"
    elif decision == "CLOSED":
        return "closed"
    return "partial"


def route_ar_maker_checker(state: FinanceState) -> str:
    """Routes Maker-Checker decision for AR."""
    gov = state.get("governance_status", {})
    if gov.get("approval_status") == "APPROVED":
        return "approved"
    return "rejected"


def build_ar_graph():
    """Assembles and compiles the Accounts Receivable (AR) workflow graph with GRC protection."""
    builder = StateGraph(FinanceState)

    # Add nodes
    builder.add_node("extract_remittance", extract_remittance_node)
    builder.add_node("lookup_invoices", lookup_invoices_node)
    builder.add_node("reconcile_payment", reconcile_payment_node)
    builder.add_node("calculate_aging", calculate_aging_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("governance_policy", ar_governance_policy_check_node)
    builder.add_node("maker_checker", ar_maker_checker_review_node)
    builder.add_node("generate_overdue", generate_overdue_reminder_node)
    builder.add_node("human_review", ar_human_review_node)

    # Add edges
    builder.add_edge(START, "extract_remittance")
    builder.add_edge("extract_remittance", "lookup_invoices")
    builder.add_edge("lookup_invoices", "reconcile_payment")
    builder.add_edge("reconcile_payment", "calculate_aging")
    builder.add_edge("calculate_aging", "risk_assessment")
    builder.add_edge("risk_assessment", "governance_policy")

    # Conditional routing edge from governance_policy
    builder.add_conditional_edges(
        "governance_policy",
        route_ar_governance,
        {
            "maker_checker": "maker_checker",
            "closed": END,
            "partial": END,
            "overdue": "generate_overdue",
            "hitl": "human_review",
        },
    )

    builder.add_conditional_edges(
        "maker_checker",
        route_ar_maker_checker,
        {
            "approved": END,
            "rejected": END,
        },
    )

    builder.add_edge("generate_overdue", "human_review")
    builder.add_edge("human_review", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory, interrupt_before=["human_review", "maker_checker"])


ar_graph = build_ar_graph()

