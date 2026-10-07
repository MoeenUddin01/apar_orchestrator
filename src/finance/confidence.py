from typing import Dict, Any, List
import os

# Default thresholds (would be loaded from config/env in production)
CONFIDENCE_THRESHOLD_CRITICAL = float(os.getenv("CONFIDENCE_THRESHOLD_CRITICAL", "0.90"))
CONFIDENCE_THRESHOLD_OVERALL = float(os.getenv("CONFIDENCE_THRESHOLD_OVERALL", "0.85"))

CRITICAL_FIELDS = ["invoice_number", "vendor_id", "po_number", "invoice_total"]

def evaluate_extraction_confidence(extraction_metadata: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the confidence scores of the extracted fields.
    Returns a dictionary detailing if the confidence passes thresholds and any reasons why it might fail.
    """
    if not extraction_metadata:
        return {
            "passes_confidence": False,
            "reasons": ["Missing extraction metadata or confidence scores."]
        }
        
    scores = extraction_metadata.get("confidence_scores", {})
    overall_score = scores.get("all", 1.0)
    
    reasons = []
    
    if overall_score < CONFIDENCE_THRESHOLD_OVERALL:
        reasons.append(f"Overall confidence ({overall_score}) is below threshold ({CONFIDENCE_THRESHOLD_OVERALL}).")
        
    for field in CRITICAL_FIELDS:
        # Check if field was extracted at all (null, empty, or UNKNOWN)
        val = extracted_data.get(field)
        if val is None or val == "" or val == "UNKNOWN" or "UNKNOWN" in str(val):
            reasons.append(f"Critical field '{field}' is missing or UNKNOWN.")
            continue
            
        # Check field level confidence if provided by provider
        field_score = scores.get(field)
        if field_score is not None and field_score < CONFIDENCE_THRESHOLD_CRITICAL:
            reasons.append(f"Critical field '{field}' confidence ({field_score}) is below threshold ({CONFIDENCE_THRESHOLD_CRITICAL}).")

    return {
        "passes_confidence": len(reasons) == 0,
        "reasons": reasons
    }
