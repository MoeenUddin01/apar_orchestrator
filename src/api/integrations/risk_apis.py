from datetime import datetime, timezone
from typing import Dict, Optional
from pydantic import BaseModel, Field
from src.domain.risk_state import RiskCategory, RiskFlag, RiskLevel


class VendorRiskProfile(BaseModel):
    vendor_id: str
    risk_rating: RiskLevel = RiskLevel.LOW
    credit_score: int = 750
    watchlist_flag: bool = False
    sanctions_clear: bool = True
    country_risk_level: RiskLevel = RiskLevel.LOW
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExternalRiskProviderException(Exception):
    """Raised when external risk provider times out or fails."""
    pass


class VendorRiskClient:
    """External API Client for dynamic vendor risk lookup and sanction screening."""

    def __init__(
        self,
        mock_db: Optional[Dict[str, VendorRiskProfile]] = None,
        simulate_failure: bool = False,
        simulate_timeout: bool = False,
    ):
        self._simulate_failure = simulate_failure
        self._simulate_timeout = simulate_timeout
        self._mock_db = mock_db or {
            "VEND-HIGH-RISK": VendorRiskProfile(
                vendor_id="VEND-HIGH-RISK",
                risk_rating=RiskLevel.HIGH,
                credit_score=420,
                watchlist_flag=True,
                sanctions_clear=True,
            ),
            "VEND-SANCTIONED": VendorRiskProfile(
                vendor_id="VEND-SANCTIONED",
                risk_rating=RiskLevel.CRITICAL,
                credit_score=300,
                watchlist_flag=True,
                sanctions_clear=False,
            ),
        }

    def get_vendor_risk_profile(self, vendor_id: str) -> VendorRiskProfile:
        """Retrieves dynamic vendor risk profile from external database/API."""
        if self._simulate_timeout:
            raise ExternalRiskProviderException("External vendor risk API request timed out after 5.0s.")
        if self._simulate_failure:
            raise ExternalRiskProviderException("External vendor risk API server connection error (503 Service Unavailable).")

        if not vendor_id:
            raise ValueError("vendor_id cannot be empty.")

        if vendor_id in self._mock_db:
            return self._mock_db[vendor_id]

        # Default clean vendor profile for unknown vendor
        return VendorRiskProfile(vendor_id=vendor_id)

    def evaluate_vendor_external_risk(self, vendor_id: str) -> Optional[RiskFlag]:
        """
        Evaluates vendor against sanctions and watchlist registries, returning RiskFlag if flagged or if API fails.
        Guarantees that API failures do NOT silently collapse to LOW risk!
        """
        try:
            profile = self.get_vendor_risk_profile(vendor_id)
        except ExternalRiskProviderException as exc:
            # External API failure handled safely as a MEDIUM severity warning flag
            return RiskFlag(
                code="EXTERNAL_RISK_API_UNAVAILABLE",
                category=RiskCategory.EXTERNAL,
                message=f"Unable to verify external risk profile for vendor '{vendor_id}': {str(exc)}.",
                severity=RiskLevel.MEDIUM,
                source="external_risk_api",
                details={"vendor_id": vendor_id, "error": str(exc)},
            )
        except Exception as exc:
            return RiskFlag(
                code="EXTERNAL_RISK_API_ERROR",
                category=RiskCategory.EXTERNAL,
                message=f"Unexpected error during external risk lookup for vendor '{vendor_id}': {str(exc)}.",
                severity=RiskLevel.MEDIUM,
                source="external_risk_api",
                details={"vendor_id": vendor_id, "error": str(exc)},
            )

        if not profile.sanctions_clear:
            return RiskFlag(
                code="VENDOR_SANCTION_MATCH",
                category=RiskCategory.SECURITY,
                message=f"Vendor '{vendor_id}' matched international sanctions registry!",
                severity=RiskLevel.CRITICAL,
                source="external_sanctions_registry",
                details={"vendor_id": vendor_id, "profile": profile.model_dump()},
            )

        if profile.watchlist_flag or profile.risk_rating in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return RiskFlag(
                code="VENDOR_HIGH_RISK_PROFILE",
                category=RiskCategory.VENDOR,
                message=f"Vendor '{vendor_id}' is on compliance watchlist (Credit Score: {profile.credit_score}).",
                severity=profile.risk_rating,
                source="external_watchlist_api",
                details={"vendor_id": vendor_id, "profile": profile.model_dump()},
            )

        return None
