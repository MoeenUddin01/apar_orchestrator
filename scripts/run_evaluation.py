import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.llm.extractors.invoice_extractor import extract_invoice_from_raw_document
from src.llm.extractors.remittance_extractor import extract_remittance_from_raw_document

def evaluate_ap_extraction():
    print("--- Evaluating AP Invoice Extraction ---")
    # Test cases: (Input text, Expected Invoice Number)
    test_cases = [
        ('{"invoice_number": "INV-100", "vendor_id": "VEND-1", "po_number": "PO-100", "invoice_total": 500.0}', "INV-100"),
        ('Invoice #: INV-999\nVendor: VEND-XYZ\nPO: PO-777\nTotal: $1,200.50', "INV-999"),
        ('Bad format invoice without standard names. inv-number is missing.', "INV-1001"), # Fallback
    ]
    
    passed = 0
    for i, (text, expected_inv) in enumerate(test_cases):
        result = extract_invoice_from_raw_document(text)
        if result.invoice_number == expected_inv:
            passed += 1
            print(f"Test {i+1} PASSED")
        else:
            print(f"Test {i+1} FAILED: Expected {expected_inv}, got {result.invoice_number}")
            
    print(f"AP Extraction Accuracy: {passed / len(test_cases) * 100:.2f}%")
    return passed == len(test_cases)

def evaluate_ar_extraction():
    print("--- Evaluating AR Remittance Extraction ---")
    test_cases = [
        ('{"remittance_id": "REM-100", "customer_id": "CUST-1", "total_payment": 200.0}', "REM-100"),
        ('Remittance: REM-555\nCustomer: CUST-ABC\nTotal Payment: $3,450.00', "REM-555"),
    ]
    
    passed = 0
    for i, (text, expected_rem) in enumerate(test_cases):
        result = extract_remittance_from_raw_document(text)
        if result.remittance_id == expected_rem:
            passed += 1
            print(f"Test {i+1} PASSED")
        else:
            print(f"Test {i+1} FAILED: Expected {expected_rem}, got {result.remittance_id}")
            
    print(f"AR Extraction Accuracy: {passed / len(test_cases) * 100:.2f}%")
    return passed == len(test_cases)

if __name__ == "__main__":
    print("Starting Extraction Evaluation...")
    ap_ok = evaluate_ap_extraction()
    print("")
    ar_ok = evaluate_ar_extraction()
    
    if ap_ok and ar_ok:
        print("\nAll evaluations passed.")
        sys.exit(0)
    else:
        print("\nSome evaluations failed.")
        sys.exit(1)
