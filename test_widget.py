"""
Automated verification suite for dscr_widget.html.

Loads the widget locally (file://) with Playwright's sync API and
exercises 5 concrete scenarios end-to-end in a real headless browser:

  a. Standard qualifying loan
  b. High-leverage / 100% LTV edge case
  c. Division-by-zero & negative-input resilience
  d. Tier boundary values (DSCR exactly 1.00 and exactly 1.25)
  e. Mobile viewport responsiveness at 375px

Run:
    python test_widget.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

WIDGET_PATH = pathlib.Path(__file__).parent / "dscr_widget.html"
WIDGET_URL = WIDGET_PATH.resolve().as_uri()

FIELD_IDS = {
    "property_value": "dw-property-value",
    "loan_amount": "dw-loan-amount",
    "interest_rate": "dw-interest-rate",
    "amort_years": "dw-amort-years",
    "monthly_rent": "dw-monthly-rent",
    "annual_taxes": "dw-annual-taxes",
    "annual_insurance": "dw-annual-insurance",
    "monthly_hoa": "dw-monthly-hoa",
}

PASS_LOG = []


def log(msg):
    PASS_LOG.append(msg)
    print(msg)


def set_inputs(page, values):
    """Fill only the fields present in `values`, leaving others untouched."""
    for key, val in values.items():
        field_id = FIELD_IDS[key]
        locator = page.locator(f"#{field_id}")
        locator.fill(str(val))
        # Force blur so 'change' also fires, matching real user behavior.
        locator.dispatch_event("change")
    # One extra input on the last touched field to guarantee the final
    # 'input' listener has settled before we read outputs.
    page.wait_for_timeout(50)


def get_outputs(page):
    return {
        "pitia": page.locator("#dw-out-pitia").inner_text(),
        "dscr_text": page.locator("#dw-out-dscr").inner_text(),
        "yield_text": page.locator("#dw-out-yield").inner_text(),
        "tier": page.locator("#dw-badge").get_attribute("data-tier"),
        "badge_text": page.locator("#dw-badge-text").inner_text(),
    }


def parse_dscr(dscr_text):
    if dscr_text in ("N/A", ""):
        return None
    return float(dscr_text)


def fresh_page(browser):
    page = browser.new_page()
    page.goto(WIDGET_URL)
    page.wait_for_selector("#dwRoot")
    return page


# ---------------------------------------------------------------------
# a. Standard qualifying loan
# ---------------------------------------------------------------------
def test_standard_qualifying_loan(browser):
    page = fresh_page(browser)
    try:
        set_inputs(page, {
            "property_value": 400000,
            "loan_amount": 300000,
            "interest_rate": 7,
            "amort_years": 30,
            "monthly_rent": 3200,
            "annual_taxes": 4000,
            "annual_insurance": 1500,
            "monthly_hoa": 0,
        })
        out = get_outputs(page)
        dscr = parse_dscr(out["dscr_text"])

        assert dscr is not None, "DSCR should be a real number for a standard loan"
        assert dscr > 1.20, f"expected DSCR > 1.20, got {dscr}"
        assert out["tier"] == "1", f"expected Tier 1 (Strong), got tier={out['tier']!r}"
        assert "Strong" in out["badge_text"], f"expected Strong Approval badge, got {out['badge_text']!r}"

        log(f"[PASS] a. Standard qualifying loan -> DSCR={dscr:.2f}, "
            f"tier={out['tier']} ({out['badge_text']}), PITIA={out['pitia']}")
    finally:
        page.close()


# ---------------------------------------------------------------------
# b. High-leverage edge case (0% down / 100% LTV)
# ---------------------------------------------------------------------
def test_high_leverage_100_ltv(browser):
    page = fresh_page(browser)
    try:
        set_inputs(page, {
            "property_value": 300000,
            "loan_amount": 300000,  # 100% LTV, no down payment
            "interest_rate": 8.5,
            "amort_years": 30,
            "monthly_rent": 2100,
            "annual_taxes": 3600,
            "annual_insurance": 1400,
            "monthly_hoa": 50,
        })
        out = get_outputs(page)
        dscr = parse_dscr(out["dscr_text"])

        assert dscr is not None, "DSCR should compute even at 100% LTV"
        assert dscr > 0, f"DSCR must be positive, got {dscr}"
        assert out["tier"] in ("0", "1", "2"), f"unexpected tier value {out['tier']!r}"
        # Higher leverage + higher rate should push this into the weaker
        # tiers relative to scenario (a); just confirm it lands in the
        # tier that matches its own numbers rather than always Tier 1.
        if dscr >= 1.25:
            expected_tier = "1"
        elif dscr >= 1.00:
            expected_tier = "2"
        else:
            expected_tier = "0"
        assert out["tier"] == expected_tier, (
            f"tier/DSCR mismatch: DSCR={dscr}, tier={out['tier']}, expected {expected_tier}"
        )

        log(f"[PASS] b. High-leverage 100% LTV -> DSCR={dscr:.2f}, "
            f"tier={out['tier']} ({out['badge_text']}), no crash at full leverage")
    finally:
        page.close()


# ---------------------------------------------------------------------
# c. Division-by-zero / negative-input resilience
# ---------------------------------------------------------------------
def test_zero_and_negative_resilience(browser):
    page = fresh_page(browser)
    try:
        # All-zero inputs -> PITIA is 0 -> DSCR is mathematically undefined.
        set_inputs(page, {
            "property_value": 0,
            "loan_amount": 0,
            "interest_rate": 0,
            "amort_years": 0,
            "monthly_rent": 0,
            "annual_taxes": 0,
            "annual_insurance": 0,
            "monthly_hoa": 0,
        })
        out = get_outputs(page)
        assert out["dscr_text"] != "NaN", "DSCR output must never render literal NaN"
        assert "Infinity" not in out["dscr_text"], "DSCR output must never render Infinity"
        assert out["pitia"] != "NaN", "PITIA output must never render literal NaN"
        log(f"[PASS] c1. All-zero inputs -> DSCR={out['dscr_text']!r}, "
            f"PITIA={out['pitia']!r} (no NaN/Infinity, no crash)")

        # Negative inputs across every field -> must clamp gracefully,
        # never crash the page and never surface NaN.
        set_inputs(page, {
            "property_value": -400000,
            "loan_amount": -300000,
            "interest_rate": -7,
            "amort_years": -30,
            "monthly_rent": -3200,
            "annual_taxes": -4000,
            "annual_insurance": -1500,
            "monthly_hoa": -50,
        })
        out = get_outputs(page)
        assert out["dscr_text"] != "NaN", "negative inputs must not produce NaN"
        assert "Infinity" not in out["dscr_text"], "negative inputs must not produce Infinity"
        assert out["pitia"] != "NaN", "negative inputs must not produce NaN PITIA"
        assert "-" not in out["pitia"] or out["pitia"] == "N/A", (
            f"PITIA should clamp to non-negative, got {out['pitia']!r}"
        )

        # Page must still be alive and interactive (no uncaught exception
        # tore down the script context).
        assert page.locator("#dwRoot").is_visible(), "widget root should still be rendered"

        log(f"[PASS] c2. All-negative inputs -> DSCR={out['dscr_text']!r}, "
            f"PITIA={out['pitia']!r} (clamped, no crash, UI still responsive)")
    finally:
        page.close()


# ---------------------------------------------------------------------
# d. Boundary values: DSCR exactly 1.00 and exactly 1.25
# ---------------------------------------------------------------------
def test_tier_boundaries(browser):
    page = fresh_page(browser)
    try:
        # Zero out the loan (PI=0) and taxes/insurance so monthly HOA is
        # the *entire* PITIA — gives us an exact, clean PITIA value to
        # build precise DSCR boundary ratios against.
        base = {
            "property_value": 100000,
            "loan_amount": 0,
            "interest_rate": 0,
            "amort_years": 30,
            "annual_taxes": 0,
            "annual_insurance": 0,
            "monthly_hoa": 1000,  # PITIA == 1000 exactly
        }

        # DSCR == 1.00 exactly -> should land in Tier 2 (Acceptable), the
        # inclusive lower bound per spec ("1.00 <= DSCR < 1.25").
        set_inputs(page, dict(base, monthly_rent=1000))
        out = get_outputs(page)
        dscr = parse_dscr(out["dscr_text"])
        assert dscr == 1.00, f"expected exact DSCR 1.00, got {dscr}"
        assert out["tier"] == "2", (
            f"DSCR==1.00 must be Tier 2 (Acceptable), got tier={out['tier']!r} "
            f"({out['badge_text']!r})"
        )
        log(f"[PASS] d1. DSCR exactly 1.00 -> tier={out['tier']} ({out['badge_text']})")

        # DSCR == 1.25 exactly -> should land in Tier 1 (Strong), the
        # inclusive lower bound of the top tier.
        set_inputs(page, dict(base, monthly_rent=1250))
        out = get_outputs(page)
        dscr = parse_dscr(out["dscr_text"])
        assert dscr == 1.25, f"expected exact DSCR 1.25, got {dscr}"
        assert out["tier"] == "1", (
            f"DSCR==1.25 must be Tier 1 (Strong), got tier={out['tier']!r} "
            f"({out['badge_text']!r})"
        )
        log(f"[PASS] d2. DSCR exactly 1.25 -> tier={out['tier']} ({out['badge_text']})")

        # Just below each boundary should fall into the weaker tier.
        set_inputs(page, dict(base, monthly_rent=999))
        out = get_outputs(page)
        assert out["tier"] == "0", f"DSCR just under 1.00 must be Ineligible, got {out['tier']!r}"
        log(f"[PASS] d3. DSCR 0.999 -> tier={out['tier']} ({out['badge_text']}) (Ineligible)")

        set_inputs(page, dict(base, monthly_rent=1249))
        out = get_outputs(page)
        assert out["tier"] == "2", f"DSCR just under 1.25 must be Tier 2, got {out['tier']!r}"
        log(f"[PASS] d4. DSCR 1.249 -> tier={out['tier']} ({out['badge_text']}) (Acceptable)")
    finally:
        page.close()


# ---------------------------------------------------------------------
# e. Viewport responsiveness at 375px (mobile)
# ---------------------------------------------------------------------
def test_mobile_viewport_375(browser):
    page = browser.new_page(viewport={"width": 375, "height": 812})
    try:
        page.goto(WIDGET_URL)
        page.wait_for_selector("#dwRoot")
        set_inputs(page, {
            "property_value": 400000,
            "loan_amount": 300000,
            "interest_rate": 7,
            "amort_years": 30,
            "monthly_rent": 3200,
            "annual_taxes": 4000,
            "annual_insurance": 1500,
            "monthly_hoa": 0,
        })

        # No horizontal overflow of the document at 375px.
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        client_width = page.evaluate("document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, (
            f"horizontal overflow at 375px viewport: scrollWidth={scroll_width} "
            f"> clientWidth={client_width}"
        )

        # The widget root itself must fit inside the viewport.
        root_box = page.locator("#dwRoot").bounding_box()
        assert root_box is not None, "widget root not rendered at 375px"
        assert root_box["width"] <= 375 + 1, (
            f"widget root wider than 375px viewport: {root_box['width']}"
        )

        # Input grid should have collapsed to a single column below the
        # 480px breakpoint (each field's row spans (nearly) the full
        # widget width rather than sitting two-per-row).
        first_field_box = page.locator("#dw-property-value").bounding_box()
        second_field_box = page.locator("#dw-loan-amount").bounding_box()
        assert first_field_box is not None and second_field_box is not None
        assert abs(first_field_box["y"] - second_field_box["y"]) > 5, (
            "expected inputs to stack vertically (single column) at 375px, "
            "but they appear on the same row"
        )

        # Key interactive elements must still be visible and usable.
        for locator_id in ("#dw-out-dscr", "#dw-badge", "#dw-embed-toggle"):
            assert page.locator(locator_id).is_visible(), f"{locator_id} not visible at 375px"

        # Embed toggle should still function on mobile.
        page.locator("#dw-embed-toggle").click()
        assert page.locator("#dw-embed-panel").evaluate(
            "el => el.classList.contains('dw-open')"
        ), "embed panel did not open on mobile viewport"
        embed_code = page.locator("#dw-embed-code").input_value()
        assert "<iframe" in embed_code, "embed snippet missing <iframe markup"

        log("[PASS] e. Mobile viewport (375px) -> no horizontal overflow, "
            "single-column layout, all controls visible and functional")
    finally:
        page.close()


# ---------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------
def main():
    if not WIDGET_PATH.exists():
        print(f"[FAIL] widget file not found: {WIDGET_PATH}")
        sys.exit(1)

    tests = [
        test_standard_qualifying_loan,
        test_high_leverage_100_ltv,
        test_zero_and_negative_resilience,
        test_tier_boundaries,
        test_mobile_viewport_375,
    ]

    failures = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for test in tests:
                try:
                    test(browser)
                except AssertionError as e:
                    failures.append((test.__name__, str(e)))
                    print(f"[FAIL] {test.__name__}: {e}")
                except Exception as e:  # noqa: BLE001 - report any crash as a failure
                    failures.append((test.__name__, f"unexpected error: {e}"))
                    print(f"[FAIL] {test.__name__}: unexpected error: {e}")
        finally:
            browser.close()

    print("\n" + "=" * 60)
    print(f"RESULTS: {len(tests) - len(failures)}/{len(tests)} scenarios passed")
    print("=" * 60)
    for line in PASS_LOG:
        print(line)

    if failures:
        print("\nFAILURES:")
        for name, msg in failures:
            print(f"  - {name}: {msg}")
        sys.exit(1)

    print("\nAll scenarios passed. 100% pass rate.")
    sys.exit(0)


if __name__ == "__main__":
    main()
