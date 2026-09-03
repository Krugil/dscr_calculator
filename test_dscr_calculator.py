"""
test_dscr_calculator.py — automated real-browser verification of the DSCR calculator.

Setup (one time):
    pip install playwright
    playwright install chromium

Usage:
    python test_dscr_calculator.py

Run `python serve.py` first, then point TARGET_URL at it (or at the live page).
Every expected value is computed HERE, independently, from the same real
formula — never hardcoded from what the calculator itself claimed.
"""

from playwright.sync_api import sync_playwright
import re
import random

# ============================================================
# Point this at local file OR live URL
# ============================================================
TARGET_URL = "http://localhost:8140/"   # start serve.py first
# TARGET_URL = "https://krugil.github.io/dscr_calculator/"


def expected_dscr(gross, expenses, loan, annual_rate_pct, term_years, freq_per_year,
                  interest_only=False):
    """The one real source of truth for correct math — independent of the app.
    Interest-only debt service is the periodic interest charge alone (L * r),
    with no principal component."""
    r = (annual_rate_pct / 100) / freq_per_year
    n = term_years * freq_per_year
    if interest_only:
        pmt = loan * r
    elif r == 0:
        pmt = loan / n
    else:
        pmt = (loan * r) / (1 - (1 + r) ** (-n))
    noi = gross - expenses
    dscr = noi / pmt if pmt else float("inf")
    return round(dscr, 2), round(pmt, 2), round(noi, 2)


# ============================================================
# Real test cases — verified presets + edge cases
# ============================================================
BASE_TEST_CASES = [
    # name, gross, expenses, loan, rate%, term_years, freq_per_year
    ("Case A (verified)",   10000, 3000, 200000, 5,    20, 12),
    ("Case B (verified)",    8000, 2500, 150000, 4,    15, 1),
    ("Case C (verified)",   12500, 4000, 250000, 6,    25, 12),
    ("Edge: near-zero rate", 10000, 3000, 200000, 0.01, 20, 12),
    ("Edge: 1-year term",    10000, 3000, 200000, 5,    1,  12),
    ("Edge: DSCR near 1.0",   9000, 3000, 500000, 6,    20, 12),
    ("Edge: large loan",     50000, 15000, 5000000, 5,  30, 12),
    ("Edge: zero expenses",  10000, 0,    200000, 5,    20, 12),
]

TEST_CASES = []

for name, gross, expenses, loan, rate, term, freq in BASE_TEST_CASES:
    exp_dscr, exp_pmt, exp_noi = expected_dscr(gross, expenses, loan, rate, term, freq)
    TEST_CASES.append((name, gross, expenses, loan, rate, term, freq, False, exp_dscr, exp_pmt, exp_noi))

# Every verified base case re-run as interest-only, where debt service is the
# periodic interest charge alone. Rates of 0 are skipped: interest-only at 0%
# is a degenerate no-payment loan with an undefined ratio, handled in the UI
# rather than asserted as a number here.
for name, gross, expenses, loan, rate, term, freq in BASE_TEST_CASES:
    if rate <= 0:
        continue
    exp_dscr, exp_pmt, exp_noi = expected_dscr(gross, expenses, loan, rate, term, freq,
                                               interest_only=True)
    TEST_CASES.append((f"{name} [interest-only]", gross, expenses, loan, rate, term, freq,
                       True, exp_dscr, exp_pmt, exp_noi))

# ============================================================
# Append 1,000 Random Scenario Checks
# Explicitly calls expected_dscr() for every single scenario
# ============================================================
random.seed(42)
for i in range(1, 1001):
    r_gross = round(random.uniform(2000, 100000), 2)
    r_expenses = round(random.uniform(0, r_gross * 0.8), 2)
    r_loan = round(random.uniform(50000, 5000000), 2)
    r_rate = round(random.uniform(0.1, 15.0), 2)
    r_term = random.randint(1, 40)
    r_freq = random.choice([12, 1])

    # Explicitly calculate expected math values using expected_dscr()
    exp_dscr, exp_pmt, exp_noi = expected_dscr(
        r_gross, r_expenses, r_loan, r_rate, r_term, r_freq
    )

    TEST_CASES.append((
        f"Random Scenario #{i:04d}",
        r_gross,
        r_expenses,
        r_loan,
        r_rate,
        r_term,
        r_freq,
        False,
        exp_dscr,
        exp_pmt,
        exp_noi
    ))

# 250 randomized interest-only scenarios, same independent-expectation pattern.
random.seed(2026)
for i in range(1, 251):
    r_gross = round(random.uniform(2000, 100000), 2)
    r_expenses = round(random.uniform(0, r_gross * 0.8), 2)
    r_loan = round(random.uniform(50000, 5000000), 2)
    r_rate = round(random.uniform(0.5, 15.0), 2)
    r_term = random.randint(1, 40)
    r_freq = random.choice([12, 1])

    exp_dscr, exp_pmt, exp_noi = expected_dscr(
        r_gross, r_expenses, r_loan, r_rate, r_term, r_freq, interest_only=True
    )
    TEST_CASES.append((
        f"Random IO Scenario #{i:04d}",
        r_gross, r_expenses, r_loan, r_rate, r_term, r_freq, True,
        exp_dscr, exp_pmt, exp_noi
    ))


def fill_and_calculate(page, gross, expenses, loan, rate, term, freq_per_year,
                       interest_only=False):
    """
    Fills out the DSCR calculator form using exact element IDs from index.html:
    #gross, #expenses, #loan, #interest, #term, #frequency, #calcBtn
    """
    page.fill("#gross", str(gross))
    page.fill("#expenses", str(expenses))
    page.fill("#loan", str(loan))
    page.fill("#interest", str(rate))
    page.fill("#term", str(term))

    freq_value = "monthly" if freq_per_year == 12 else "annual"
    page.select_option("#frequency", freq_value)

    if page.is_checked("#interestOnly") != interest_only:
        page.set_checked("#interestOnly", interest_only)

    page.click("#calcBtn")


def read_displayed_dscr(page):
    """Pull the real rendered DSCR number off the page via #dscrValue element."""
    text = page.locator("#dscrValue").inner_text()
    match = re.search(r"([\d.]+)", text)
    return float(match.group(1)) if match else None


def run_tests():
    print(f"Starting execution of {len(TEST_CASES)} automated checks against:\n{TARGET_URL}\n")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TARGET_URL)

        for idx, (name, gross, expenses, loan, rate, term, freq, io_mode, expected, exp_pmt, exp_noi) in enumerate(TEST_CASES, 1):
            try:
                fill_and_calculate(page, gross, expenses, loan, rate, term, freq, io_mode)
                displayed = read_displayed_dscr(page)
                if displayed is None:
                    results.append((name, "FAIL", "No DSCR value found on page", expected, None))
                elif abs(displayed - expected) <= 0.02:
                    results.append((name, "PASS", "", expected, displayed))
                else:
                    results.append((name, "FAIL", "Mismatch", expected, displayed))
            except Exception as e:
                results.append((name, "ERROR", str(e), expected, None))

            if idx % 100 == 0:
                print(f"Progress: Completed {idx}/{len(TEST_CASES)} checks...")

        browser.close()

    print(f"\n{'Test Case':<28} {'Result':<8} {'Expected':<10} {'Got':<10} Notes")
    print("-" * 80)
    for name, status, note, expected, got in results[:15]:
        print(f"{name:<28} {status:<8} {expected!s:<10} {got!s:<10} {note}")

    if len(results) > 15:
        print(f"... [{len(results) - 15} additional test scenarios evaluated] ...")

    fails = [r for r in results if r[1] != "PASS"]
    if fails:
        print(f"\nSummary: {len(results) - len(fails)}/{len(results)} passed. {len(fails)} failures detected.")
        print("\nFailures:")
        for name, status, note, expected, got in fails[:20]:
            print(f"  {name}: Expected {expected}, Got {got} ({note})")
    else:
        print(f"\nSummary: {len(results)}/{len(results)} passed (100% success rate).")
        print("All automated checks passed successfully with zero math or UI discrepancies!")


if __name__ == "__main__":
    run_tests()
