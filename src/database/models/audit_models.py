from sqlalchemy import Boolean, Column, Float, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from src.database.connection import Base


class AuditEventDB(Base):
    __tablename__ = "audit_events"

    event_id = Column(String, primary_key=True, index=True)
    timestamp = Column(String, nullable=False, index=True)
    workflow_id = Column(String, nullable=False, index=True)
    workflow_type = Column(String, nullable=True, index=True)
    transaction_id = Column(String, nullable=True, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    
    actor_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    actor_role = Column(String, nullable=True, index=True)
    
    event_type = Column(String, nullable=False, index=True)
    grc_domain = Column(String, nullable=True, index=True)
    node_name = Column(String, nullable=True)
    
    action = Column(String, nullable=True)
    decision = Column(String, nullable=True)
    status = Column(String, nullable=False, default="SUCCESS")
    
    reason = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    result = Column(String, nullable=True)
    
    # Backcheck & Risk / Governance Columns
    risk_level = Column(String, nullable=True, index=True)
    risk_score = Column(Float, nullable=True)
    risk_flags = Column(JSONB, default=[])
    approval_required = Column(Boolean, nullable=True)
    approval_status = Column(String, nullable=True, index=True)

    evidence_refs = Column(JSONB, default=[])
    metadata_json = Column("metadata", JSONB, default={})
    
    previous_hash = Column(String, nullable=True)
    event_hash = Column(String, nullable=False)
