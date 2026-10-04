# Phase 4: Human-in-the-Loop (HITL)

## 1. Phase Objective
Integrate Human-in-the-Loop (HITL) functionality into both AP and AR workflows using LangGraph checkpointers. This allows the graph to pause execution deterministically when an exception, dispute, or high-value threshold is met, awaiting manual API intervention before resuming.

## 2. Architecture & Design
- **LangGraph Checkpointer**: Integrate `MemorySaver` (for dev) or Postgres checkpointing (for prod) into the LangGraph compilation step.
- **`src/finance/routing.py`**: Python rules defining thresholds (e.g., `amount > $10,000` requires approval, or `tolerance_exceeded == True`).
- **`src/api/routes/`**: Implement resume endpoints (e.g., `POST /ap/{thread_id}/approve` or `POST /ap/{thread_id}/reject`).
- **`src/graph/`**: Add interrupt nodes (`interrupt_before=["human_review_node"]`).

## 3. Technical Task List
- [x] Setup a Postgres-backed or in-memory Checkpointer for the compiled AP and AR LangGraphs.
- [x] Write deterministic rules in `finance/routing.py` to identify states requiring human review (Exceptions, Disputes, High-Value).
- [x] Configure LangGraph to pause execution when the routing decision targets a `human_review` node.
- [x] Expose an API endpoint to retrieve the current pending state of a paused workflow.
- [x] Expose API endpoints to inject human input (Approve, Reject, Override) into the paused state.
- [x] Update the LangGraph workflows to resume execution seamlessly upon receiving the API human input.

## 4. Input/Output Requirements
**Routing Output (Python boundary)**:
```python
class RoutingDecision(BaseModel):
    requires_hitl: bool
    hitl_reason: Optional[Literal["HIGH_VALUE", "TOLERANCE_EXCEPTION", "MISSING_DOCS"]]
```

**API Resume Input**:
```json
{
    "action": "APPROVE",
    "comments": "Variance approved by manager."
}
```

## 5. Acceptance Criteria
- LangGraph correctly pauses execution before transitioning to final states if `requires_hitl` is true.
- The paused workflow state is fully retrievable via an API call.
- Sending an API payload with a human decision successfully resumes the workflow from exactly where it paused.
- All routing conditions leading to HITL are governed by deterministic variables in the `FinanceState`, not LLM judgments.
