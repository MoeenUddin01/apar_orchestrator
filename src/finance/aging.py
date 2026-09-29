from datetime import date, datetime
from typing import Literal


def calculate_days_overdue(due_date_str: str, current_date: date | None = None) -> int:
    """
    Pure deterministic Python logic to calculate days overdue.
    Returns 0 if due_date is in the future.
    """
    if current_date is None:
        current_date = date.today()

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0

    delta = (current_date - due_date).days
    return max(0, delta)


def get_aging_bucket(days_overdue: int) -> Literal["CURRENT", "30_DAYS", "60_DAYS", "90_DAYS_PLUS"]:
    """
    Categorizes days overdue into standard accounting aging buckets.
    """
    if days_overdue <= 0:
        return "CURRENT"
    elif days_overdue <= 30:
        return "30_DAYS"
    elif days_overdue <= 60:
        return "60_DAYS"
    else:
        return "90_DAYS_PLUS"
