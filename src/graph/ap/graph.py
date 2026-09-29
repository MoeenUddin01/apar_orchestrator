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
from src.graph.state import FinanceState


def build_ap_graph():
    """Assembles and compiles the Accounts Payable (AP) workflow graph."""
    builder = StateGraph(FinanceState)

    # Add nodes
    builder.add_node("extract_invoice", extract_invoice_node)
    builder.add_node("validate_invoice", validate_invoice_node)
    builder.add_node("lookup_db", lookup_db_node)
    builder.add_node("match_3_way", match_3_way_node)
    builder.add_node("generate_discrepancy", generate_discrepancy_notice_node)
    builder.add_node("human_review", human_review_node)

    # Add edges
    builder.add_edge(START, "extract_invoice")
    builder.add_edge("extract_invoice", "validate_invoice")
    builder.add_edge("validate_invoice", "lookup_db")
    builder.add_edge("lookup_db", "match_3_way")

    # Conditional routing edge from 3-way match
    builder.add_conditional_edges(
        "match_3_way",
        route_ap_decision,
        {
            "approve": END,
            "exception": END,
            "hitl": "generate_discrepancy",
        },
    )
    
    # Path from generate_discrepancy to human_review
    builder.add_edge("generate_discrepancy", "human_review")
    # Path from human review to END
    builder.add_edge("human_review", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory, interrupt_before=["human_review"])


ap_graph = build_ap_graph()
