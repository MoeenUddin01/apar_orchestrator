import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from src.core.hashing import compute_event_hash, verify_chain as check_chain_integrity
from src.core.security.redaction import default_redactor
from src.database.models.audit_models import AuditEventDB
from src.domain.audit_schema import AuditEvent

logger = logging.getLogger(__name__)


class AuditRepository:
    """
    Append-only repository for storing and querying tamper-evident audit events.
    Supports in-memory persistence as well as database session integration.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        # In-memory store for fast access and fallback testing
        self._in_memory_events: List[AuditEvent] = []
        self._index_by_id: Dict[str, AuditEvent] = {}

    def log_event(self, event: AuditEvent) -> AuditEvent:
        """
        Appends an event to the audit trail.
        Redacts PII, chains previous_hash, computes event_hash, and persists entry.
        """
        # 1. PII Redaction on summary and metadata
        redacted_meta, _ = default_redactor.redact_dict(event.metadata or {})
        redacted_summary = (
            default_redactor.redact_text(event.summary).redacted_text
            if event.summary
            else None
        )

        event.metadata = redacted_meta
        event.summary = redacted_summary

        # 2. Cryptographic Hash Chaining
        workflow_events = self.get_workflow_events(event.workflow_id)
        if workflow_events:
            event.previous_hash = workflow_events[-1].event_hash
        else:
            event.previous_hash = event.previous_hash or ""

        # Compute hash if not pre-computed or if recalculated
        event.event_hash = compute_event_hash(event, previous_hash=event.previous_hash)

        # 3. Save to In-Memory store
        self._in_memory_events.append(event)
        self._index_by_id[event.event_id] = event

        # 4. Save to DB Session if available
        if self.session:
            try:
                db_record = AuditEventDB(
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    workflow_id=event.workflow_id,
                    correlation_id=event.correlation_id,
                    actor_type=str(event.actor_type),
                    actor_id=event.actor_id,
                    event_type=str(event.event_type),
                    node_name=event.node_name,
                    status=event.status,
                    result=event.result,
                    summary=event.summary,
                    evidence_refs=event.evidence_refs,
                    metadata_json=event.metadata,
                    previous_hash=event.previous_hash,
                    event_hash=event.event_hash,
                )
                self.session.add(db_record)
                self.session.commit()
            except Exception as e:
                logger.error(f"Failed to commit audit record to DB: {e}")
                if self.session:
                    self.session.rollback()

        return event

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Retrieves a single audit event by ID."""
        if event_id in self._index_by_id:
            return self._index_by_id[event_id]

        if self.session:
            record = (
                self.session.query(AuditEventDB)
                .filter(AuditEventDB.event_id == event_id)
                .first()
            )
            if record:
                return self._to_domain_model(record)

        return None

    def get_workflow_events(self, workflow_id: str) -> List[AuditEvent]:
        """Retrieves all audit events associated with a specific workflow, ordered by sequence."""
        in_mem_matches = [
            ev for ev in self._in_memory_events if ev.workflow_id == workflow_id
        ]
        if in_mem_matches:
            return in_mem_matches

        if self.session:
            records = (
                self.session.query(AuditEventDB)
                .filter(AuditEventDB.workflow_id == workflow_id)
                .order_by(AuditEventDB.timestamp.asc())
                .all()
            )
            return [self._to_domain_model(r) for r in records]

        return []

    def get_correlation_events(self, correlation_id: str) -> List[AuditEvent]:
        """Retrieves cross-workflow audit events linked by correlation_id."""
        in_mem_matches = [
            ev for ev in self._in_memory_events if ev.correlation_id == correlation_id
        ]
        if in_mem_matches:
            return in_mem_matches

        if self.session:
            records = (
                self.session.query(AuditEventDB)
                .filter(AuditEventDB.correlation_id == correlation_id)
                .order_by(AuditEventDB.timestamp.asc())
                .all()
            )
            return [self._to_domain_model(r) for r in records]

        return []

    def verify_chain(self, workflow_id: str) -> Tuple[bool, Optional[str]]:
        """Verifies the hash chain integrity for all events in a workflow."""
        events = self.get_workflow_events(workflow_id)
        return check_chain_integrity(events)

    def query_reports(
        self,
        event_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[AuditEvent]:
        """Queries audit trail events for reporting and compliance audits."""
        events = list(self._in_memory_events)
        if event_type:
            events = [ev for ev in events if str(ev.event_type) == event_type]
        if start_time:
            events = [ev for ev in events if ev.timestamp >= start_time]
        if end_time:
            events = [ev for ev in events if ev.timestamp <= end_time]
        return events

    def clear(self):
        """Clears in-memory audit logs (useful for test isolation)."""
        self._in_memory_events.clear()
        self._index_by_id.clear()

    def _to_domain_model(self, record: AuditEventDB) -> AuditEvent:
        return AuditEvent(
            event_id=record.event_id,
            timestamp=record.timestamp,
            workflow_id=record.workflow_id,
            correlation_id=record.correlation_id,
            actor_type=record.actor_type,
            actor_id=record.actor_id,
            event_type=record.event_type,
            node_name=record.node_name,
            status=record.status,
            result=record.result,
            summary=record.summary,
            evidence_refs=record.evidence_refs or [],
            metadata=record.metadata_json or {},
            previous_hash=record.previous_hash,
            event_hash=record.event_hash,
        )


# Global default repository instance for in-memory graph execution
default_audit_repository = AuditRepository()
