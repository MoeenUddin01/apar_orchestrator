from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from src.database.connection import Base


class AuditEventDB(Base):
    __tablename__ = "audit_events"

    event_id = Column(String, primary_key=True, index=True)
    timestamp = Column(String, nullable=False, index=True)
    workflow_id = Column(String, nullable=False, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    node_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="SUCCESS")
    result = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    evidence_refs = Column(JSONB, default=[])
    metadata_json = Column("metadata", JSONB, default={})
    previous_hash = Column(String, nullable=True)
    event_hash = Column(String, nullable=False)
