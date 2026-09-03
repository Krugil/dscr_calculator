"""
test_dscr_visual.py -- visual / geometric / mobile regression checks for the
DSCR calculator, complementing test_dscr_calculator.py's math checks. Run this
AGAINST A FRESH LOCAL SERVER (serve.py), never a raw file:// URL and never a
long-running server you haven't restarted since your last edit -- stale cached
CSS/HTML produced repeated false readings during earlier work on these sites.

Checks, in order:
  G1. Gauge needle geometry -- the needle's tip is recomputed here from the
      DSCR via an independent replication of the polar math and compared to the
      rendered coordinates within 1px, across several ratios including the
      clamped above-scale case.
  G2. Hub/needle origin alignment -- the needle must start exactly at the hub.
  G3. Band arc endpoints -- the three qualification arcs must begin and end at
      the exact angles for 0 / 1.00x / 1.25x / 2.00x.
  G4. No clipping -- every rendered gauge element stays inside the viewBox at
      375px, 640px and 1280px.
  1.  Input prefix/suffix clearance (the shipped "$ overlaps the number" bug).
  2.  Desktop table sanity, 3. mobile overflow, 4. mobile table reflow,
      4b. gauge renders at mobile, 5. nav toggle.
  6.  Interest-only toggle: debt service falls, DSCR rises, max loan grows.
  7.  Above-the-fold fit on desktop.

Setup: pip install playwright && playwright install chromium
"""

from playwright.sync_api import sync_playwright
import math
import os
import re
import sys
import io

# This machine's console defaults to cp1252, which mangles any non-ASCII in
# printed page text even when the underlying string is correct.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TARGET_URL = "http://localhost:8140/"
SCREENSHOT_DIR = "visual_check_screenshots"

# ===================================================================
# These MUST mirror the GAUGE constants and renderQualificationGauge()
# in script.js. Every expected coordinate is computed here independently --
# the page's own emitted geometry is never the source of truth.
# ===================================================================
G_W, G_H = 460.0, 212.0
G_CX, G_CY, G_R = 230.0, 190.0, 140.0
G_MAX_DSCR = 2.0
G_BAND = 20.0
NEEDLE_INNER_R = 86.0             # must match NEEDLE_INNER_R in script.js
NEEDLE_OUTER_R = 116.0            # must match NEEDLE_OUTER_R in script.js
PRIME = 1.25


def gauge_angle_for(dscr):
    clamped = min(max(dscr, 0.0), G_MAX_DSCR)
    return 180.0 - (clamped / G_MAX_DSCR) * 180.0


def gauge_point(radius, angle_deg):
    rad = math.radians(angle_deg)
    return (G_CX + radius * math.cos(rad), G_CY - radius * math.sin(rad))


def read_gauge(page):
    return page.evaluate("""
        () => {
            const svg = document.getElementById('qualificationGauge');
            if (!svg) return null;
            const needle = svg.querySelector('#gaugeNeedle');
            const hub = svg.querySelector('#gaugeHub');
            const arcs = [...svg.querySelectorAll('path')].map(p => ({
                d: p.getAttribute('d'), stroke: p.getAttribute('stroke')
            }));
            const boxes = [];
            svg.querySelectorAll('*').forEach(el => {
                const tag = el.tagName.toLowerCase();
                if (['defs', 'lineargradient', 'stop'].includes(tag)) return;
                try {
                    const b = el.getBBox();
                    boxes.push({tag: el.tagName, x: b.x, y: b.y, w: b.width, h: b.height});
                } catch (e) {}
            });
            return {
                needle: needle ? {
                    x1: parseFloat(needle.getAttribute('x1')),
                    y1: parseFloat(needle.getAttribute('y1')),
                    x2: parseFloat(needle.getAttribute('x2')),
                    y2: parseFloat(needle.getAttribute('y2'))
                } : null,
                hub: hub ? {
                    cx: parseFloat(hub.getAttribute('cx')),
                    cy: parseFloat(hub.getAttribute('cy'))
                } : null,
                arcs, boxes
            };
        }
    """)


def arc_endpoints(d_attr):
    """Pulls (startX, startY, endX, endY) out of an 'M x y A r r 0 f f x y' path."""
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", d_attr)]
    # M sx sy A r r rot largeArc sweep ex ey
    return (nums[0], nums[1], nums[-2], nums[-1])


def set_inputs(page, gross, expenses, loan, interest, term, frequency="monthly", io=False):
    page.fill("#gross", str(gross))
    page.fill("#expenses", str(expenses))
    page.fill("#loan", str(loan))
    page.fill("#interest", str(interest))
    page.fill("#term", str(term))
    page.select_option("#frequency", frequency)
    if page.is_checked("#interestOnly") != io:
        page.set_checked("#interestOnly", io)
    page.wait_for_timeout(220)


def expected_dscr(gross, expenses, loan, rate_pct, term_years, freq_per_year, io=False):
    r = (rate_pct / 100) / freq_per_year
    n = term_years * freq_per_year
    if io:
        pmt = loan * r
    elif r == 0:
        pmt = loan / n
    else:
        pmt = (loan * r) / (1 - (1 + r) ** (-n))
    noi = gross - expenses
    return (noi / pmt) if pmt else 0.0


def run_gauge_geometry_checks(browser):
    failed = False

    # (label, gross, expenses, loan, rate, term, freq_per_year, expected tier)
    CASES = [
        ("high risk (~0.66x)",   10000, 3000, 1600000, 5, 20, 12),
        ("marginal (~1.06x)",    10000, 3000, 1000000, 5, 20, 12),
        ("just under prime",     10000, 3000,  900000, 5, 20, 12),
        ("prime (~1.3x)",        10000, 3000,  810000, 5, 20, 12),
        ("above 2.0x scale",     10000, 3000,  200000, 5, 20, 12),
    ]

    print("=== G1. Gauge needle geometry (rendered vs independently computed) ===")
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(TARGET_URL)
    page.wait_for_timeout(300)

    for label, gross, exp, loan, rate, term, freq in CASES:
        set_inputs(page, gross, exp, loan, rate, term, "monthly")
        dscr = expected_dscr(gross, exp, loan, rate, term, freq)
        g = read_gauge(page)

        if not g or not g["needle"]:
            print(f"  [FAIL] {label}: no needle rendered")
            failed = True
            continue

        angle = gauge_angle_for(dscr)
        ix, iy = gauge_point(NEEDLE_INNER_R, angle)
        ox, oy = gauge_point(NEEDLE_OUTER_R, angle)
        worst = max(abs(g["needle"]["x1"] - ix), abs(g["needle"]["y1"] - iy),
                    abs(g["needle"]["x2"] - ox), abs(g["needle"]["y2"] - oy))
        if worst <= 1.0:
            print(f"  [OK]   {label}: DSCR {dscr:.2f}x -> pointer "
                  f"({g['needle']['x1']:.1f},{g['needle']['y1']:.1f})->"
                  f"({g['needle']['x2']:.1f},{g['needle']['y2']:.1f}) "
                  f"within {worst:.2f}px of the {angle:.1f}deg ray")
        else:
            print(f"  [FAIL] {label}: pointer off the {angle:.1f}deg ray by {worst:.2f}px -- "
                  f"got ({g['needle']['x1']:.1f},{g['needle']['y1']:.1f})->"
                  f"({g['needle']['x2']:.1f},{g['needle']['y2']:.1f}), "
                  f"expected ({ix:.1f},{iy:.1f})->({ox:.1f},{oy:.1f})")
            failed = True

    # --- G2: the pointer must be strictly radial (both ends on one ray through
    # the gauge centre) and must not intrude on the tier label in the middle.
    print("\n=== G2. Pointer is strictly radial and clears the centre label ===")
    g = read_gauge(page)
    if g["needle"]:
        n = g["needle"]
        r_in = math.hypot(n["x1"] - G_CX, n["y1"] - G_CY)
        r_out = math.hypot(n["x2"] - G_CX, n["y2"] - G_CY)
        ang_in = math.degrees(math.atan2(G_CY - n["y1"], n["x1"] - G_CX))
        ang_out = math.degrees(math.atan2(G_CY - n["y2"], n["x2"] - G_CX))
        radial = abs(ang_in - ang_out) < 0.05
        radii_ok = abs(r_in - NEEDLE_INNER_R) < 0.5 and abs(r_out - NEEDLE_OUTER_R) < 0.5
        clears_label = r_in >= 60          # tier label sits within ~50px of centre
        if radial and radii_ok and clears_label:
            print(f"  [OK]   both ends on one {ang_in:.1f}deg ray, radii {r_in:.1f}->{r_out:.1f}px, "
                  f"inner end clears the centre label")
        else:
            print(f"  [FAIL] radial={radial} (angles {ang_in:.2f} vs {ang_out:.2f}), "
                  f"radii {r_in:.1f}/{r_out:.1f} (expected {NEEDLE_INNER_R}/{NEEDLE_OUTER_R}), "
                  f"clears_label={clears_label}")
            failed = True
    else:
        print("  [FAIL] pointer missing")
        failed = True

    # --- G3: the three qualification bands must span the exact tier angles
    print("\n=== G3. Qualification band arc endpoints ===")
    arcs = [a for a in g["arcs"] if a["stroke"] and a["stroke"] != "var(--bg-deep)"]
    expected_bands = [
        ("high risk band", 180.0, gauge_angle_for(1.0), "var(--danger-line)"),
        ("marginal band", gauge_angle_for(1.0), gauge_angle_for(PRIME), "var(--warning-line)"),
        ("prime band", gauge_angle_for(PRIME), 0.0, "var(--strong-line)"),
    ]
    if len(arcs) != len(expected_bands):
        print(f"  [FAIL] expected {len(expected_bands)} coloured bands, found {len(arcs)}")
        failed = True
    else:
        for (name, a_start, a_end, colour), arc in zip(expected_bands, arcs):
            sx, sy, ex_, ey_ = arc_endpoints(arc["d"])
            exp_s = gauge_point(G_R, a_start)
            exp_e = gauge_point(G_R, a_end)
            worst = max(abs(sx - exp_s[0]), abs(sy - exp_s[1]),
                        abs(ex_ - exp_e[0]), abs(ey_ - exp_e[1]))
            if worst <= 1.0 and arc["stroke"] == colour:
                print(f"  [OK]   {name}: {a_start:.1f}deg -> {a_end:.1f}deg, "
                      f"endpoints within {worst:.2f}px, stroke {arc['stroke']}")
            else:
                print(f"  [FAIL] {name}: endpoint deviation {worst:.2f}px, stroke {arc['stroke']} (expected {colour})")
                failed = True

    page.close()

    # --- G4: nothing escapes the viewBox at any rendered width
    print("\n=== G4. No clipping: all gauge geometry inside the 460x212 viewBox ===")
    for width in (375, 640, 1280):
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(TARGET_URL)
        set_inputs(page, 10000, 3000, 200000, 5, 20, "monthly")
        boxes = read_gauge(page)["boxes"]
        escapes = [b for b in boxes
                   if b["x"] < -0.5 or b["y"] < -0.5
                   or b["x"] + b["w"] > G_W + 0.5
                   or b["y"] + b["h"] > G_H + 0.5]
        if not escapes:
            print(f"  [OK]   {width}px: all {len(boxes)} rendered elements within the viewBox")
        else:
            print(f"  [FAIL] {width}px: {len(escapes)} element(s) escape the viewBox:")
            for b in escapes[:6]:
                print(f"         <{b['tag']}> x={b['x']:.1f} y={b['y']:.1f} w={b['w']:.1f} h={b['h']:.1f} "
                      f"(right={b['x']+b['w']:.1f}, bottom={b['y']+b['h']:.1f})")
            failed = True
        page.close()

    return failed


OVERLAP_CHECKS = [
    ("Gross income $ vs input", ".input-prefix-wrapper >> nth=0 >> .input-prefix", "#gross", False),
    ("Expenses $ vs input", ".input-prefix-wrapper >> nth=1 >> .input-prefix", "#expenses", False),
    ("Loan $ vs input", ".input-prefix-wrapper >> nth=2 >> .input-prefix", "#loan", False),
    ("Interest %% vs input", ".input-suffix-wrapper >> nth=0 >> .input-suffix", "#interest", True),
]


def check_prefix_clearance(page, prefix_loc, input_loc, is_suffix):
    box_p = prefix_loc.bounding_box()
    box_i = input_loc.bounding_box()
    if not box_p or not box_i:
        return None
    if is_suffix:
        pad = page.evaluate("(el) => parseFloat(getComputedStyle(el).paddingRight)", input_loc.element_handle())
        text_end = box_i["x"] + box_i["width"] - pad
        overlap = max(0.0, text_end - box_p["x"])
        return overlap, box_p["x"] - text_end, pad
    pad = page.evaluate("(el) => parseFloat(getComputedStyle(el).paddingLeft)", input_loc.element_handle())
    prefix_right = box_p["x"] + box_p["width"]
    text_start = box_i["x"] + pad
    overlap = max(0.0, prefix_right - text_start)
    return overlap, text_start - prefix_right, pad


def check_mobile_overflow(page):
    return page.evaluate("""
        () => {
            const trueWidth = document.documentElement.clientWidth;
            const overflowing = [];
            document.querySelectorAll('body *').forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.right > trueWidth + 1) {
                    overflowing.push({tag: el.tagName, cls: (el.className||'').toString(), right: Math.round(r.right)});
                }
            });
            return {trueWidth, scrollWidth: document.documentElement.scrollWidth, overflowing};
        }
    """)


def check_table_reflow(page):
    return page.evaluate("""
        () => {
            const thead = document.querySelector('.benchmark-table thead');
            const td = document.querySelector('.benchmark-table td');
            if (!thead || !td) return null;
            return {theadDisplay: getComputedStyle(thead).display, tdDisplay: getComputedStyle(td).display};
        }
    """)


def run_visual_checks():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    any_fail = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        if run_gauge_geometry_checks(browser):
            any_fail = True

        # ---------- Desktop pass ----------
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(TARGET_URL)
        page.click('[data-preset="caseA"]')
        page.wait_for_timeout(300)

        print("\n=== 1. Input prefix/suffix clearance checks (desktop) ===")
        for label, sel_a, sel_b, is_suffix in OVERLAP_CHECKS:
            try:
                res = check_prefix_clearance(page, page.locator(sel_a), page.locator(sel_b), is_suffix)
                if res is None:
                    print(f"  [SKIP] {label} - element not found")
                    any_fail = True
                    continue
                overlap, clearance, pad = res
                if overlap > 0:
                    print(f"  [FAIL] {label} - overlap {overlap:.1f}px (padding {pad}px)")
                    any_fail = True
                else:
                    print(f"  [OK]   {label} - no overlap (clearance {clearance:.1f}px, padding {pad}px)")
            except Exception as e:
                print(f"  [ERROR] {label} - {e}")
                any_fail = True

        print("\n=== 2. Desktop table sanity (normal table, not reflowed) ===")
        r = check_table_reflow(page)
        if r and r["theadDisplay"] != "none":
            print(f"  [OK]   thead='{r['theadDisplay']}', td='{r['tdDisplay']}'")
        else:
            print(f"  [FAIL] table unexpectedly reflowed on desktop: {r}")
            any_fail = True

        print("\n=== 6. Interest-only toggle ===")
        set_inputs(page, 10000, 3000, 200000, 5, 20, "monthly", io=False)
        amort = page.evaluate("""() => ({
            dscr: parseFloat(document.getElementById('dscrValue').textContent),
            tds: parseFloat(document.getElementById('tdsValue').textContent.replace(/[$,]/g,'')),
            maxLoan: parseFloat(document.getElementById('maxLoanValue').textContent.replace(/[$,]/g,'')),
            label: document.getElementById('tdsLabel').textContent
        })""")
        set_inputs(page, 10000, 3000, 200000, 5, 20, "monthly", io=True)
        io_state = page.evaluate("""() => ({
            dscr: parseFloat(document.getElementById('dscrValue').textContent),
            tds: parseFloat(document.getElementById('tdsValue').textContent.replace(/[$,]/g,'')),
            maxLoan: parseFloat(document.getElementById('maxLoanValue').textContent.replace(/[$,]/g,'')),
            label: document.getElementById('tdsLabel').textContent
        })""")

        # Independently expected interest-only figures
        r_per = (5 / 100) / 12
        exp_io_tds = 200000 * r_per
        exp_io_dscr = 7000 / exp_io_tds
        exp_io_max = (7000 / PRIME) / r_per

        checks = [
            ("IO debt service is the periodic interest charge",
             abs(io_state["tds"] - exp_io_tds) <= 0.02, f"{io_state['tds']:.2f} vs {exp_io_tds:.2f}"),
            ("IO DSCR matches NOI / IO payment",
             abs(io_state["dscr"] - exp_io_dscr) <= 0.01, f"{io_state['dscr']:.2f} vs {exp_io_dscr:.2f}"),
            ("IO max loan matches (NOI/1.25)/r",
             abs(io_state["maxLoan"] - exp_io_max) <= 1.0, f"{io_state['maxLoan']:.2f} vs {exp_io_max:.2f}"),
            ("IO debt service is lower than amortizing",
             io_state["tds"] < amort["tds"], f"{io_state['tds']:.2f} < {amort['tds']:.2f}"),
            ("IO DSCR is higher than amortizing",
             io_state["dscr"] > amort["dscr"], f"{io_state['dscr']:.2f} > {amort['dscr']:.2f}"),
            ("IO supports a larger loan at 1.25x",
             io_state["maxLoan"] > amort["maxLoan"], f"{io_state['maxLoan']:.0f} > {amort['maxLoan']:.0f}"),
            ("Debt service label switches to interest-only",
             "Interest-Only" in io_state["label"], io_state["label"]),
        ]
        for name, ok, detail in checks:
            print(f"  [{'OK  ' if ok else 'FAIL'}] {name} ({detail})")
            if not ok:
                any_fail = True
        page.set_checked("#interestOnly", False)

        print("\n=== 7. Calculator clears the fold on desktop ===")
        fold = page.evaluate("""() => {
            const g = document.getElementById('calculator').getBoundingClientRect();
            return {bottom: Math.round(g.bottom), vh: window.innerHeight};
        }""")
        if fold["bottom"] <= fold["vh"]:
            print(f"  [OK]   calculator bottom {fold['bottom']}px within {fold['vh']}px viewport")
        else:
            print(f"  [FAIL] calculator extends below the fold: {fold['bottom']}px vs {fold['vh']}px")
            any_fail = True

        page.screenshot(path=f"{SCREENSHOT_DIR}/dscr_desktop_full.png", full_page=True)
        page.close()

        # ---------- Mobile pass ----------
        page = browser.new_page(viewport={"width": 375, "height": 812})
        page.goto(TARGET_URL)
        page.click('[data-preset="caseA"]')
        page.wait_for_timeout(300)

        print("\n=== 3. Mobile (375px) horizontal-overflow check ===")
        o = check_mobile_overflow(page)
        if o["scrollWidth"] <= o["trueWidth"] + 1 and not o["overflowing"]:
            print(f"  [OK]   no horizontal overflow. clientWidth={o['trueWidth']}, scrollWidth={o['scrollWidth']}")
        else:
            print(f"  [FAIL] overflow! clientWidth={o['trueWidth']}, scrollWidth={o['scrollWidth']}")
            for el in o["overflowing"][:8]:
                print(f"         <{el['tag']} class=\"{el['cls']}\"> right={el['right']}px")
            any_fail = True

        print("\n=== 4. Mobile (375px) table reflow check ===")
        r = check_table_reflow(page)
        if r and r["theadDisplay"] == "none" and r["tdDisplay"] == "block":
            print("  [OK]   table reflowed into stacked cards (thead hidden, td=block)")
        else:
            print(f"  [FAIL] table did not reflow at mobile width: {r}")
            any_fail = True

        print("\n=== 4b. Mobile (375px) gauge renders inside the viewport ===")
        mg = page.evaluate("""() => {
            const svg = document.getElementById('qualificationGauge');
            const r = svg.getBoundingClientRect();
            return {w: Math.round(r.width), h: Math.round(r.height), right: Math.round(r.right),
                    paths: svg.querySelectorAll('path').length,
                    vw: document.documentElement.clientWidth};
        }""")
        if mg["paths"] >= 4 and mg["h"] > 60 and mg["right"] <= mg["vw"] + 1:
            print(f"  [OK]   gauge {mg['w']}x{mg['h']}px, {mg['paths']} arcs, within viewport")
        else:
            print(f"  [FAIL] gauge problem at mobile width: {mg}")
            any_fail = True

        print("\n=== 5. Mobile nav toggle check ===")
        before = page.evaluate("() => getComputedStyle(document.getElementById('headerNav')).display")
        page.click("#navToggle")
        page.wait_for_timeout(120)
        after = page.evaluate("() => getComputedStyle(document.getElementById('headerNav')).display")
        if before == "none" and after == "flex":
            print(f"  [OK]   nav hidden by default ('{before}'), opens on toggle ('{after}')")
        else:
            print(f"  [FAIL] nav toggle unexpected: before='{before}', after='{after}'")
            any_fail = True

        page.screenshot(path=f"{SCREENSHOT_DIR}/dscr_mobile_full.png", full_page=True)
        page.close()
        browser.close()

    print(f"\nScreenshots saved to ./{SCREENSHOT_DIR}/")
    print(f"\n{'FAIL - real issue found' if any_fail else 'All visual/geometry/mobile checks passed'}")
    return any_fail


if __name__ == "__main__":
    exit(1 if run_visual_checks() else 0)
