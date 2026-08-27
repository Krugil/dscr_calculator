"""
test_dscr_visual.py — visual regression checks, complementing test_dscr_calculator.py's
math checks. Run this ALONGSIDE the math test, not instead of it — they catch
different bug classes.

Setup: same as before (pip install playwright && playwright install chromium)
"""

from playwright.sync_api import sync_playwright
import os

TARGET_URL = "https://netdscr.com/"
SCREENSHOT_DIR = "visual_check_screenshots"

# Elements to check for real overlap — verified against index.html & style.css
# Each entry: (label, prefix_selector, input_selector)
OVERLAP_CHECKS = [
    ("Gross income $ vs input", ".input-prefix-wrapper >> nth=0 >> .input-prefix", "#gross"),
    ("Expenses $ vs input", ".input-prefix-wrapper >> nth=1 >> .input-prefix", "#expenses"),
    ("Loan $ vs input", ".input-prefix-wrapper >> nth=2 >> .input-prefix", "#loan"),
]


def check_prefix_text_clearance(page, prefix_loc, input_loc):
    """
    Real geometric layout check — calculates whether the prefix '$' icon
    extends into the input's text entry zone (input left + computed padding-left).
    """
    box_prefix = prefix_loc.bounding_box()
    box_input = input_loc.bounding_box()
    if not box_prefix or not box_input:
        return None

    padding_left = page.evaluate(
        "(el) => parseFloat(window.getComputedStyle(el).paddingLeft)",
        input_loc.element_handle()
    )

    prefix_right = box_prefix["x"] + box_prefix["width"]
    text_start = box_input["x"] + padding_left
    overlap = max(0.0, prefix_right - text_start)
    clearance = text_start - prefix_right
    return overlap, clearance, box_prefix, box_input, padding_left


def run_visual_checks():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(TARGET_URL)

        # Fill Case A so fields are non-empty (bugs often only show with real content)
        page.click('[data-preset="caseA"]')
        page.wait_for_timeout(300)

        print("Real bounding-box overlap checks:")
        any_fail = False
        for label, sel_a, sel_b in OVERLAP_CHECKS:
            try:
                loc_a = page.locator(sel_a)
                loc_b = page.locator(sel_b)
                res = check_prefix_text_clearance(page, loc_a, loc_b)
                if res is None:
                    print(f"  [SKIP] {label} - element not found, check selectors")
                    any_fail = True
                    continue

                overlap, clearance, box_prefix, box_input, pad_left = res
                if overlap > 0:
                    print(f"  [FAIL] {label} - overlap detected! Prefix invades text area by {overlap:.1f}px (padding-left: {pad_left}px)")
                    any_fail = True
                else:
                    print(f"  [OK]   {label} - no overlap (clearance: {clearance:.1f}px, padding-left: {pad_left}px)")
            except Exception as e:
                print(f"  [ERROR] {label} - {e}")
                any_fail = True

        # Full-page + focused screenshots of the wrapper (shows icon + number together)
        page.screenshot(path=f"{SCREENSHOT_DIR}/full_page.png", full_page=True)
        try:
            page.locator(".input-prefix-wrapper").nth(0).screenshot(path=f"{SCREENSHOT_DIR}/gross_field.png")
            page.locator(".input-prefix-wrapper").nth(1).screenshot(path=f"{SCREENSHOT_DIR}/expenses_field.png")
            page.locator(".input-prefix-wrapper").nth(2).screenshot(path=f"{SCREENSHOT_DIR}/loan_field.png")
        except Exception as e:
            print(f"Field screenshots partially failed: {e}")

        browser.close()

    print(f"\nScreenshots saved to ./{SCREENSHOT_DIR}/:")
    for f in os.listdir(SCREENSHOT_DIR):
        fpath = os.path.join(SCREENSHOT_DIR, f)
        size = os.path.getsize(fpath)
        print(f"  - {f} ({size:,} bytes)")

    print(f"\n{'FAIL - real issue found' if any_fail else 'All geometric checks passed'}")


if __name__ == "__main__":
    run_visual_checks()
