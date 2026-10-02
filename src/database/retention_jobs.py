from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.logging import logger


async def cleanup_expired_checkpoints(
    db: AsyncSession,
    retention_days: int = 30,
) -> Dict[str, Any]:
    """
    Purges SQL database checkpointer states older than retention_days TTL threshold to comply with GDPR/CCPA.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
    total_deleted = 0
    tables_cleaned = []

    # Known LangGraph and custom state tables
    target_tables = ["checkpoints", "checkpoint_blobs", "checkpoint_writes", "graph_states"]

    for table in target_tables:
        try:
            # Query table for records prior to cutoff_time
            stmt = text(f"DELETE FROM {table} WHERE created_at < :cutoff OR timestamp < :cutoff")
            result = await db.execute(stmt, {"cutoff": cutoff_time})
            deleted_count = result.rowcount if hasattr(result, "rowcount") else 0
            if deleted_count > 0:
                total_deleted += deleted_count
                tables_cleaned.append(f"{table} ({deleted_count} rows)")
        except Exception as exc:
            # Log table omission gracefully if table does not exist in schema
            logger.debug(f"Table '{table}' not present or error during retention cleanup: {exc}")

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error(f"Failed to commit database retention cleanup: {exc}")
        raise

    return {
        "status": "SUCCESS",
        "retention_days": retention_days,
        "cutoff_timestamp": cutoff_time.isoformat(),
        "total_records_deleted": total_deleted,
        "tables_cleaned": tables_cleaned,
    }


def cleanup_in_memory_checkpoints(
    checkpointer_store: Dict[str, Any],
    retention_seconds: float = 2592000,  # Default 30 days in seconds
) -> Dict[str, Any]:
    """
    Purges expired in-memory graph checkpointer entries based on timestamp metadata.
    """
    if not checkpointer_store or not isinstance(checkpointer_store, dict):
        return {
            "status": "SUCCESS",
            "total_records_deleted": 0,
            "remaining_records": 0,
        }

    now = datetime.now(timezone.utc).timestamp()
    keys_to_delete = []

    for thread_id, state_data in list(checkpointer_store.items()):
        # Retrieve timestamp from dictionary metadata
        ts = None
        if isinstance(state_data, dict):
            ts = state_data.get("timestamp") or state_data.get("created_at") or state_data.get("ts")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    ts = None
        elif hasattr(state_data, "timestamp"):
            ts = getattr(state_data, "timestamp")

        if ts and isinstance(ts, (int, float)):
            if (now - ts) > retention_seconds:
                keys_to_delete.append(thread_id)

    for key in keys_to_delete:
        del checkpointer_store[key]

    return {
        "status": "SUCCESS",
        "retention_seconds": retention_seconds,
        "total_records_deleted": len(keys_to_delete),
        "remaining_records": len(checkpointer_store),
        "deleted_thread_ids": keys_to_delete,
    }


async def run_data_retention_job(
    retention_days: int = 30,
    db_session: Optional[AsyncSession] = None,
    memory_store: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Unified entry point for background TTL data retention cleanup jobs.
    """
    results: Dict[str, Any] = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "retention_days": retention_days,
        "db_cleanup": None,
        "memory_cleanup": None,
    }

    if db_session:
        results["db_cleanup"] = await cleanup_expired_checkpoints(db_session, retention_days=retention_days)

    if memory_store is not None:
        results["memory_cleanup"] = cleanup_in_memory_checkpoints(
            memory_store, retention_seconds=retention_days * 86400
        )

    logger.info(f"Data retention job completed successfully. Results: {results}")
    return results
