from langgraph.graph import END, START, StateGraph
from src.graph.ar.nodes import (
    calculate_aging_node,
    extract_remittance_node,
    lookup_invoices_node,
    reconcile_payment_node,
    route_ar_decision,
)
from src.graph.state import FinanceState


def build_ar_graph():
    """Assembles and compiles the Accounts Receivable (AR) workflow graph."""
    builder = StateGraph(FinanceState)

    # Add nodes
    builder.add_node("extract_remittance", extract_remittance_node)
    builder.add_node("lookup_invoices", lookup_invoices_node)
    builder.add_node("reconcile_payment", reconcile_payment_node)
    builder.add_node("calculate_aging", calculate_aging_node)

    # Add edges
    builder.add_edge(START, "extract_remittance")
    builder.add_edge("extract_remittance", "lookup_invoices")
    builder.add_edge("lookup_invoices", "reconcile_payment")
    builder.add_edge("reconcile_payment", "calculate_aging")

    # Conditional routing edge from reconciliation & aging
    builder.add_conditional_edges(
        "calculate_aging",
        route_ar_decision,
        {
            "closed": END,
            "partial": END,
            "overdue": END,
        },
    )

    return builder.compile()


ar_graph = build_ar_graph()
