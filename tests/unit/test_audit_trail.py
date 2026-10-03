import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.hashing import compute_event_hash, verify_chain, verify_event_hash
from src.database.audit_repository import AuditRepository, default_audit_repository
from src.domain.audit_schema import ActorType, AuditEvent, EventType
from src.graph.shared.callbacks.audit_logger import AuditLoggerCallbackHandler

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_audit_repo():
    default_audit_repository.clear()
    yield
    default_audit_repository.clear()


def test_audit_schema_creation():
    event = AuditEvent(
        workflow_id="AP-TEST-001",
        actor_type=ActorType.USER,
        actor_id="user_123",
        event_type=EventType.WORKFLOW_STARTED,
        status="SUCCESS",
        summary="Workflow initiated by user",
    )
    assert event.event_id is not None
    assert event.timestamp is not None
    assert event.workflow_id == "AP-TEST-001"
    assert event.actor_type == ActorType.USER
    assert event.event_type == EventType.WORKFLOW_STARTED


def test_cryptographic_hash_computation_and_verification():
    event = AuditEvent(
        workflow_id="AP-TEST-002",
        actor_type=ActorType.SYSTEM,
        actor_id="system",
        event_type=EventType.NODE_ENTRY,
        node_name="Invoice_Extraction",
        previous_hash="",
    )
    event.event_hash = compute_event_hash(event, previous_hash="")

    assert event.event_hash is not None
    assert len(event.event_hash) == 64  # SHA-256 length
    assert verify_event_hash(event) is True

    # Alter event content to simulate tampering
    tampered_event = event.model_copy()
    tampered_event.status = "TAMPERED"
    assert verify_event_hash(tampered_event) is False


def test_hash_chain_verification():
    repo = AuditRepository()
    ev1 = repo.log_event(
        AuditEvent(
            workflow_id="WF-CHAIN-1",
            event_type=EventType.WORKFLOW_STARTED,
            actor_type=ActorType.SYSTEM,
            actor_id="engine",
        )
    )
    ev2 = repo.log_event(
        AuditEvent(
            workflow_id="WF-CHAIN-1",
            event_type=EventType.NODE_ENTRY,
            node_name="Risk_Node",
            actor_type=ActorType.SYSTEM,
            actor_id="node:Risk_Node",
        )
    )
    ev3 = repo.log_event(
        AuditEvent(
            workflow_id="WF-CHAIN-1",
            event_type=EventType.WORKFLOW_COMPLETED,
            actor_type=ActorType.SYSTEM,
            actor_id="engine",
        )
    )

    events = repo.get_workflow_events("WF-CHAIN-1")
    assert len(events) == 3

    # Check previous_hash link
    assert ev2.previous_hash == ev1.event_hash
    assert ev3.previous_hash == ev2.event_hash

    # Verify chain integrity
    is_valid, err = verify_chain(events)
    assert is_valid is True
    assert err is None


def test_hash_chain_tamper_detection():
    repo = AuditRepository()
    repo.log_event(
        AuditEvent(
            workflow_id="WF-TAMPER-1",
            event_type=EventType.WORKFLOW_STARTED,
            actor_type=ActorType.SYSTEM,
            actor_id="engine",
        )
    )
    repo.log_event(
        AuditEvent(
            workflow_id="WF-TAMPER-1",
            event_type=EventType.RISK_ASSESSMENT,
            actor_type=ActorType.SERVICE,
            actor_id="risk-service",
            status="LOW_RISK",
        )
    )

    events = repo.get_workflow_events("WF-TAMPER-1")
    # Tamper with the second event's status
    events[1].status = "HIGH_RISK"

    is_valid, err = repo.verify_chain("WF-TAMPER-1")
    assert is_valid is False
    assert "Tampering detected" in err


def test_pii_redaction_in_audit_logging():
    repo = AuditRepository()
    event = repo.log_event(
        AuditEvent(
            workflow_id="WF-PII-1",
            event_type=EventType.LLM_CALL,
            actor_type=ActorType.LLM_AGENT,
            actor_id="gpt-4",
            summary="User submitted SSN 123-45-6789 for vendor.",
            metadata={"bank_account": "GB82WEST12345698765432"},
        )
    )

    assert "[REDACTED_SSN]" in event.summary
    assert "123-45-6789" not in event.summary
    assert "[REDACTED_BANK_ACCOUNT]" in str(event.metadata)


def test_langgraph_callback_handler():
    cb = AuditLoggerCallbackHandler(repository=default_audit_repository)
    wf_id = "WF-CB-100"

    cb.on_workflow_start(wf_id, correlation_id="CORR-100")
    cb.on_node_entry("Risk_Assessment", wf_id)
    cb.on_risk_assessment(wf_id, risk_level="MEDIUM_RISK", risk_flags=[], action="REVIEW")
    cb.on_node_exit("Risk_Assessment", wf_id, status="SUCCESS")
    cb.on_governance_decision(wf_id, decision="APPROVED", policy_code="POL-001")
    cb.on_maker_checker_action(wf_id, action="APPROVED", checker_id="checker_01")
    cb.on_workflow_complete(wf_id, correlation_id="CORR-100")

    events = default_audit_repository.get_workflow_events(wf_id)
    assert len(events) == 7

    # Verify chain integrity
    is_valid, err = default_audit_repository.verify_chain(wf_id)
    assert is_valid is True
    assert err is None


def test_audit_api_endpoints():
    cb = AuditLoggerCallbackHandler(repository=default_audit_repository)
    wf_id = "WF-API-200"

    ev_start = cb.on_workflow_start(wf_id, correlation_id="CORR-API")
    cb.on_node_entry("Compliance_Node", wf_id)
    cb.on_compliance_assessment(wf_id, status="PASS", findings=[])
    cb.on_workflow_complete(wf_id, correlation_id="CORR-API")

    # GET /api/v1/audit/events/{id}
    res_ev = client.get(f"/audit/events/{ev_start.event_id}")
    assert res_ev.status_code == 200
    assert res_ev.json()["event_id"] == ev_start.event_id

    # GET /api/v1/audit/workflows/{wf_id}
    res_wf = client.get(f"/audit/workflows/{wf_id}")
    assert res_wf.status_code == 200
    assert len(res_wf.json()) == 4

    # GET /api/v1/audit/workflows/{wf_id}/verify
    res_verify = client.get(f"/audit/workflows/{wf_id}/verify")
    assert res_verify.status_code == 200
    data_verify = res_verify.json()
    assert data_verify["is_valid"] is True
    assert data_verify["event_count"] == 4

    # GET /api/v1/audit/correlations/{correlation_id}
    res_corr = client.get("/audit/correlations/CORR-API")
    assert res_corr.status_code == 200
    assert len(res_corr.json()) == 2

    # GET /api/v1/audit/reports
    res_reports = client.get("/audit/reports?event_type=WORKFLOW_STARTED")
    assert res_reports.status_code == 200
    assert len(res_reports.json()) >= 1
