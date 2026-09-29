# Phase 1: Foundation

## 1. Phase Objective
Establish the core infrastructure and technical foundation of the AP/AR Orchestrator project. This includes setting up dependency management, API routing, database connectivity, logging, and defining the base state schema for LangGraph.

## 2. Architecture & Design
- **`pyproject.toml`**: Configure `uv` as the package manager and define standard dependencies (FastAPI, SQLAlchemy/asyncpg, LangGraph, Pydantic, etc.).
- **`src/core/`**: Implement structured logging, environment configuration mapping (`.env`), and base application exceptions.
- **`src/api/`**: Setup FastAPI entry point (`main.py`) with a base `/health` check.
- **`src/database/`**: Implement the PostgreSQL async engine and base session dependency.
- **`src/graph/state.py`**: Define `FinanceState`, a TypedDict or Pydantic model representing the shared state required for all financial LangGraph executions.

## 3. Technical Task List
- [x] Initialize the project environment using `uv init`.
- [x] Install FastAPI, Uvicorn, SQLAlchemy, LangGraph, and their dependencies.
- [x] Implement `core.config.py` using `pydantic-settings` to load `.env`.
- [x] Configure standard Python `logging` for JSON/structured log output in `core.logging.py`.
- [x] Implement database connection handling and engine creation in `database.connection.py`.
- [x] Build the FastAPI shell in `api.main.py` and register `api.routes.health.py`.
- [x] Define the base `FinanceState` schema in `graph.state.py`.
- [x] Setup initial Pytest configuration and write a test for the health endpoint.

## 4. Input/Output Requirements
**FinanceState Base Schema (`graph/state.py`)**:
```python
class FinanceState(TypedDict):
    workflow_id: str
    workflow_type: Literal["AP", "AR"]
    status: Literal["PENDING", "PROCESSING", "REQUIRES_APPROVAL", "COMPLETED", "ERROR"]
    raw_document: Optional[str]
    extracted_data: Optional[Dict[str, Any]]
    validation_errors: List[str]
    financial_facts: Dict[str, Any]
    routing_decision: Optional[str]
```

## 5. Acceptance Criteria
- `uv sync` correctly installs all dependencies.
- FastAPI server starts successfully and `/health` returns 200 OK.
- The PostgreSQL database connection successfully connects on application startup.
- `FinanceState` is strictly typed and importable without circular dependencies.
- Pytest suite runs successfully with at least one passing test for the foundation layer.
