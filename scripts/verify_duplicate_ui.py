import time
from playwright.sync_api import sync_playwright

def clear_text(page):
    textarea = page.locator("textarea")
    textarea.fill("")

def submit_invoice(page, invoice_text, role="MAKER"):
    page.locator("div[data-testid='stSelectbox']").filter(has_text="Simulate Role").locator("input").fill(role)
    page.keyboard.press("Enter")
    time.sleep(1)
    
    clear_text(page)
    textarea = page.locator("textarea")
    textarea.fill(invoice_text)
    
    page.locator("button", has_text="Submit Document").click()
    
    try:
        page.locator("text=Submitted successfully!").wait_for(timeout=10000)
    except:
        pass
    time.sleep(4) 

def run_verification():
    print("--- Running UI Verification for Duplicate Invoice Pipeline ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8501")
        time.sleep(3)

        invoice_payload = """Invoice: INV-QA-001
PO: PO-1001
Vendor: VEND-101
Line Items:
- item_id: ITEM-102, quantity: 6.0, unit_price: 200.0, total_price: 1200.0
Total: 1200"""

        # 1. First submission
        print("\n[Step 1] Submitting INV-QA-001 for the first time...")
        submit_invoice(page, invoice_payload)
        
        try:
            expander_1 = page.locator("div[data-testid='stExpanderDetails']").nth(0).inner_text()
            print("First Submission Result:")
            print(expander_1[:500])
        except Exception as e:
            print(f"Could not read expander 1: {e}")

        # 2. Second submission (Resubmit identical invoice)
        print("\n[Step 2] Resubmitting the same INV-QA-001...")
        submit_invoice(page, invoice_payload)

        try:
            expander_2 = page.locator("div[data-testid='stExpanderDetails']").nth(0).inner_text()
            print("\nSecond Submission Result:")
            print(expander_2.replace('\n\n', '\n'))
        except Exception as e:
            print(f"Could not read expander 2: {e}")

        browser.close()

if __name__ == "__main__":
    run_verification()
