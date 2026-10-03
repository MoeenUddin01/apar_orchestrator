import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Union

from src.domain.audit_schema import AuditEvent


def _canonicalize_dict(data: Dict[str, Any]) -> str:
    """Recursively canonicalizes dictionary data into deterministic JSON string."""

    def json_default(obj):
        if hasattr(obj, "value"):  # Handles Enums
            return obj.value
        return str(obj)

    return json.dumps(data, sort_keys=True, default=json_default)


def compute_event_hash(
    event: Union[Dict[str, Any], AuditEvent],
    previous_hash: Optional[str] = None,
) -> str:
    """Computes SHA-256 event hash by chaining previous_hash + canonical event payload."""
    if isinstance(event, AuditEvent):
        event_dict = event.model_dump(exclude={"event_hash"})
    else:
        event_dict = dict(event)
        event_dict.pop("event_hash", None)

    # Use explicitly passed previous_hash if given, else use what's inside event dict
    prev_hash_str = previous_hash if previous_hash is not None else (event_dict.get("previous_hash") or "")
    event_dict["previous_hash"] = prev_hash_str

    canonical_data = _canonicalize_dict(event_dict)
    combined = f"{prev_hash_str}:{canonical_data}"

    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def verify_event_hash(event: AuditEvent) -> bool:
    """Verifies that an event's event_hash matches its content calculation."""
    if not event.event_hash:
        return False
    expected_hash = compute_event_hash(event, previous_hash=event.previous_hash)
    return event.event_hash == expected_hash


def verify_chain(events: List[AuditEvent]) -> Tuple[bool, Optional[str]]:
    """
    Verifies cryptographic hash chain integrity across a sequence of audit events.
    Returns (True, None) if intact, or (False, failure_reason) if broken or tampered.
    """
    if not events:
        return True, None

    for i, event in enumerate(events):
        # 1. Verify self-hash integrity
        if not verify_event_hash(event):
            return (
                False,
                f"Tampering detected: Event '{event.event_id}' (index {i}) hash mismatch.",
            )

        # 2. Verify hash chain connection with previous event
        if i > 0:
            prev_event = events[i - 1]
            if event.previous_hash != prev_event.event_hash:
                return (
                    False,
                    f"Chain broken at index {i}: Event '{event.event_id}' previous_hash "
                    f"'{event.previous_hash}' does not match previous event_hash '{prev_event.event_hash}'.",
                )

    return True, None
