// DSCR Calculator Core Engine

const presets = {
  caseA: { gross: 10000, expenses: 3000, loan: 200000, interest: 5, term: 20, frequency: 'monthly' },
  caseB: { gross: 8000, expenses: 2500, loan: 150000, interest: 4, term: 15, frequency: 'annual' },
  caseC: { gross: 12500, expenses: 4000, loan: 250000, interest: 6, term: 25, frequency: 'monthly' }
};

// The conventional prime underwriting threshold, and the ratio the "Max Loan"
// output is sized against.
const PRIME_DSCR_THRESHOLD = 1.25;

// Gauge geometry. Every one of these is asserted against in
// test_dscr_visual.py, which recomputes the needle position independently --
// so changing any of them without updating that test will fail the suite.
const GAUGE = { W: 460, H: 212, CX: 230, CY: 190, R: 140, MAX_DSCR: 2.0 };

// Radial extent of the pointer, measured from the gauge centre. Kept clear of
// the tier label that sits in the middle of the dial.
const NEEDLE_INNER_R = 86;
const NEEDLE_OUTER_R = 116;

/**
 * Converts annual percentage interest rate to periodic decimal rate
 */
function periodicInterestRate(annualRatePercent, frequency) {
  const annualDecimal = annualRatePercent / 100;
  if (frequency === 'monthly') {
    return annualDecimal / 12;
  }
  return annualDecimal; // annual
}

/**
 * Standard fixed-rate loan amortization periodic payment formula
 * P = (L * r) / (1 - (1 + r)^(-n))
 */
function computePeriodicPayment(loan, rate, nPayments) {
  if (nPayments <= 0) return 0;
  if (rate === 0) return loan / nPayments;
  const factor = Math.pow(1 + rate, nPayments);
  return (loan * rate * factor) / (factor - 1);
}

/**
 * Interest-only periodic debt service: the periodic interest charge alone,
 * with no principal amortization. Always lower than the amortizing payment
 * for the same principal, which is why an interest-only structure supports a
 * larger loan at the same coverage ratio.
 */
function computeInterestOnlyPayment(loan, rate) {
  return loan * rate;
}

/**
 * Inverse of the payment formulas above: the largest loan whose periodic debt
 * service is exactly `payment`. Used to size the maximum loan a property's NOI
 * supports at the prime coverage threshold.
 *   Amortizing:     L = P * (1 - (1 + r)^-n) / r
 *   Interest-only:  L = P / r
 * Returns Infinity for the degenerate interest-only-at-0%-rate case (no
 * interest means no debt service, so no loan size is constrained) -- callers
 * must render that as unavailable rather than as a number.
 */
function computeMaxLoanForPayment(payment, rate, nPayments, interestOnly) {
  if (payment <= 0) return 0;
  if (interestOnly) {
    return rate > 0 ? payment / rate : Infinity;
  }
  if (nPayments <= 0) return 0;
  if (rate === 0) return payment * nPayments;
  return payment * (1 - Math.pow(1 + rate, -nPayments)) / rate;
}

/**
 * Format currency with commas and 2 decimals
 */
function formatCurrency(num) {
  if (isNaN(num) || !isFinite(num)) return '$0.00';
  return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/* ==================== Qualification gauge ==================== */

/** DSCR -> gauge angle in degrees. 0x sits at 180 (left), MAX_DSCR at 0 (right). */
function gaugeAngleFor(dscr) {
  const clamped = Math.min(Math.max(dscr, 0), GAUGE.MAX_DSCR);
  return 180 - (clamped / GAUGE.MAX_DSCR) * 180;
}

/** Polar -> cartesian in SVG space (y grows downward, hence the minus). */
function gaugePoint(radius, angleDeg) {
  const rad = (angleDeg * Math.PI) / 180;
  return {
    x: GAUGE.CX + radius * Math.cos(rad),
    y: GAUGE.CY - radius * Math.sin(rad)
  };
}

/** Arc sweeping clockwise on screen from startDeg down to endDeg. */
function gaugeArcPath(radius, startDeg, endDeg) {
  const s = gaugePoint(radius, startDeg);
  const e = gaugePoint(radius, endDeg);
  const largeArc = Math.abs(startDeg - endDeg) > 180 ? 1 : 0;
  return `M ${s.x.toFixed(2)} ${s.y.toFixed(2)} A ${radius} ${radius} 0 ${largeArc} 1 ${e.x.toFixed(2)} ${e.y.toFixed(2)}`;
}

function renderQualificationGauge(dscr, hasResult) {
  const svg = document.getElementById('qualificationGauge');
  if (!svg) return;

  const BAND = 20;                       // arc stroke width
  const arcR = GAUGE.R;
  const a1_00 = gaugeAngleFor(1.0);      // 90deg
  const a1_25 = gaugeAngleFor(PRIME_DSCR_THRESHOLD); // 67.5deg

  const bands = [
    { d: gaugeArcPath(arcR, 180, a1_00), color: 'var(--danger-line)' },
    { d: gaugeArcPath(arcR, a1_00, a1_25), color: 'var(--warning-line)' },
    { d: gaugeArcPath(arcR, a1_25, 0), color: 'var(--strong-line)' }
  ].map(b =>
    `<path d="${b.d}" fill="none" stroke="${b.color}" stroke-width="${BAND}" stroke-linecap="butt"/>`
  ).join('');

  // Tick labels sit just outside the band.
  const tickR = arcR + BAND / 2 + 14;
  const ticks = [
    { dscr: 0, label: '0' },
    { dscr: 1.0, label: '1.00x' },
    { dscr: PRIME_DSCR_THRESHOLD, label: '1.25x' },
    { dscr: GAUGE.MAX_DSCR, label: '2.00x+' }
  ].map(t => {
    const isEnd = t.dscr === 0 || t.dscr >= GAUGE.MAX_DSCR;
    const p = gaugePoint(tickR, gaugeAngleFor(t.dscr));
    const anchor = t.dscr === 0 ? 'start' : (t.dscr >= GAUGE.MAX_DSCR ? 'end' : 'middle');
    // The end ticks drop below the arc line: a needle clamped to 0deg (any DSCR
    // at or above the 2.0x cap) lies exactly along y = CY and ran straight
    // through the "2.00x+" label when it sat at the same height.
    const ty = isEnd ? p.y + 15 : p.y;
    return `<text x="${p.x.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="${anchor}"
             font-size="12" font-weight="600" fill="var(--text-muted)"
             font-family="system-ui, sans-serif">${t.label}</text>`;
  }).join('');

  // The threshold marker: a short radial tick straight through the band at 1.25x.
  const thrInner = gaugePoint(arcR - BAND / 2 - 2, a1_25);
  const thrOuter = gaugePoint(arcR + BAND / 2 + 2, a1_25);
  const thresholdMark =
    `<line x1="${thrInner.x.toFixed(1)}" y1="${thrInner.y.toFixed(1)}"
           x2="${thrOuter.x.toFixed(1)}" y2="${thrOuter.y.toFixed(1)}"
           stroke="var(--text)" stroke-width="2"/>`;

  // A floating radial pointer rather than a full needle from the centre: a
  // full-length needle sweeps straight through the tier label sitting in the
  // middle of the gauge (confirmed -- at ~1.06x it ran right across the word
  // "MARGINAL"). Both endpoints still lie exactly on the DSCR's radial ray,
  // which test_dscr_visual.py asserts independently.
  const needleAngle = gaugeAngleFor(hasResult ? dscr : 0);
  const pInner = gaugePoint(NEEDLE_INNER_R, needleAngle);
  const pOuter = gaugePoint(NEEDLE_OUTER_R, needleAngle);
  const needle = hasResult
    ? `<line id="gaugeNeedle" x1="${pInner.x.toFixed(2)}" y1="${pInner.y.toFixed(2)}"
             x2="${pOuter.x.toFixed(2)}" y2="${pOuter.y.toFixed(2)}"
             stroke="var(--text)" stroke-width="4" stroke-linecap="round"/>`
    : '';

  // The centre of the gauge labels the TIER the needle is pointing at rather
  // than repeating the DSCR figure -- the banner directly above already shows
  // that number at 3rem, so echoing it here added noise and no information.
  const tierLabel =
    dscr < 1.0 ? 'HIGH RISK' :
    dscr < PRIME_DSCR_THRESHOLD ? 'MARGINAL' :
    dscr < 1.5 ? 'PRIME' : 'STRONG';
  const tierColor =
    dscr < 1.0 ? 'var(--danger)' :
    dscr < PRIME_DSCR_THRESHOLD ? 'var(--warning)' :
    'var(--strong)';
  const readout = hasResult
    ? `<text x="${GAUGE.CX}" y="${GAUGE.CY - 40}" text-anchor="middle"
             font-size="17" font-weight="800" letter-spacing="1.5" fill="${tierColor}"
             font-family="system-ui, sans-serif">${tierLabel}</text>
       <text x="${GAUGE.CX}" y="${GAUGE.CY - 21}" text-anchor="middle"
             font-size="11" font-weight="600" fill="var(--text-muted)"
             font-family="system-ui, sans-serif">${dscr >= GAUGE.MAX_DSCR ? 'above the 2.00x scale' : 'vs 1.25x threshold'}</text>`
    : '';

  svg.innerHTML = `
    <path d="${gaugeArcPath(arcR, 180, 0)}" fill="none" stroke="var(--bg-deep)" stroke-width="${BAND}"/>
    ${bands}
    ${thresholdMark}
    ${ticks}
    ${readout}
    ${needle}
  `;
}

/**
 * Main Calculation Routine
 */
function calculateDSCR() {
  const gross = parseFloat(document.getElementById('gross').value) || 0;
  const expenses = parseFloat(document.getElementById('expenses').value) || 0;
  const loan = parseFloat(document.getElementById('loan').value) || 0;
  const interest = parseFloat(document.getElementById('interest').value) || 0;
  const termYears = parseFloat(document.getElementById('term').value) || 0;
  const frequency = document.getElementById('frequency').value;
  const interestOnly = document.getElementById('interestOnly').checked;

  if (loan <= 0 || termYears <= 0) {
    return;
  }

  const paymentsPerYear = frequency === 'monthly' ? 12 : 1;
  const totalPayments = termYears * paymentsPerYear;
  const periodicRate = periodicInterestRate(interest, frequency);

  // Total periodic debt service (TDS)
  const tds = interestOnly
    ? computeInterestOnlyPayment(loan, periodicRate)
    : computePeriodicPayment(loan, periodicRate, totalPayments);

  // Net Operating Income (NOI)
  const noi = gross - expenses;

  // DSCR calculation
  const dscr = tds > 0 ? (noi / tds) : 0;

  // Cash flow & annualized figures
  const netCashFlow = noi - tds;
  const annualizedTds = tds * paymentsPerYear;

  // Largest loan this NOI supports at the prime coverage threshold, using the
  // same rate/term/frequency and the same amortizing-vs-interest-only basis.
  const maxLoan = computeMaxLoanForPayment(
    noi / PRIME_DSCR_THRESHOLD, periodicRate, totalPayments, interestOnly
  );

  // DOM Elements
  const dscrValueEl = document.getElementById('dscrValue');
  const dscrStatusEl = document.getElementById('dscrStatus');
  const statusBadgeEl = document.getElementById('statusBadge');
  const amortModePillEl = document.getElementById('amortModePill');
  const noiValueEl = document.getElementById('noiValue');
  const tdsValueEl = document.getElementById('tdsValue');
  const tdsLabelEl = document.getElementById('tdsLabel');
  const cashFlowValueEl = document.getElementById('cashFlowValue');
  const annualDebtValueEl = document.getElementById('annualDebtValue');
  const maxLoanValueEl = document.getElementById('maxLoanValue');
  const banner = document.getElementById('resultsBanner');
  const gaugeSubtitle = document.getElementById('gaugeSubtitle');

  // Update Metric Text
  dscrValueEl.textContent = isFinite(dscr) ? dscr.toFixed(2) + 'x' : '—';
  noiValueEl.textContent = formatCurrency(noi);
  tdsValueEl.textContent = formatCurrency(tds);
  tdsLabelEl.textContent = interestOnly
    ? (frequency === 'monthly' ? 'Interest-Only (Monthly)' : 'Interest-Only (Annual)')
    : (frequency === 'monthly' ? 'Debt Service (Monthly)' : 'Debt Service (Annual)');
  cashFlowValueEl.textContent = formatCurrency(netCashFlow);
  annualDebtValueEl.textContent = formatCurrency(annualizedTds);
  maxLoanValueEl.textContent = isFinite(maxLoan) ? formatCurrency(maxLoan) : '—';

  amortModePillEl.textContent = interestOnly ? 'Interest-Only' : 'Amortizing';
  amortModePillEl.className = interestOnly ? 'badge is-io' : 'badge';
  amortModePillEl.title = interestOnly
    ? 'Debt service is the periodic interest charge only, with no principal amortization. Lenders typically still qualify borrowers on the eventual amortizing payment.'
    : 'Debt service is the fully amortizing principal + interest payment over the loan term.';

  // Status & Badge Evaluation
  let statusKey, badgeText;

  if (dscr < 1.0) {
    statusKey = 'danger';
    badgeText = 'High Risk';
    dscrStatusEl.textContent = 'High default risk — operating income cannot cover debt obligations.';
  } else if (dscr < PRIME_DSCR_THRESHOLD) {
    statusKey = 'warning';
    badgeText = 'Marginal';
    dscrStatusEl.textContent = 'Tight eligibility — below the conventional 1.25x prime lender benchmark.';
  } else if (dscr < 1.50) {
    statusKey = 'success';
    badgeText = 'Prime Approval';
    dscrStatusEl.textContent = 'Meets or exceeds standard commercial lender requirements.';
  } else {
    statusKey = 'strong';
    badgeText = 'Strong / Low Risk';
    dscrStatusEl.textContent = 'Substantial income buffer over required debt service.';
  }

  statusBadgeEl.className = `badge badge-${statusKey}`;
  statusBadgeEl.textContent = badgeText;
  banner.className = `results-banner status-${statusKey}`;

  const shortfall = PRIME_DSCR_THRESHOLD - dscr;
  gaugeSubtitle.textContent = dscr >= PRIME_DSCR_THRESHOLD
    ? `${(dscr - PRIME_DSCR_THRESHOLD).toFixed(2)}x above the 1.25x prime threshold`
    : `${shortfall.toFixed(2)}x below the 1.25x prime threshold`;

  renderQualificationGauge(dscr, true);
}

/**
 * Load Preset Values
 */
function loadPreset(presetKey) {
  const p = presets[presetKey];
  if (!p) return;
  document.getElementById('gross').value = p.gross;
  document.getElementById('expenses').value = p.expenses;
  document.getElementById('loan').value = p.loan;
  document.getElementById('interest').value = p.interest;
  document.getElementById('term').value = p.term;
  document.getElementById('frequency').value = p.frequency;
  calculateDSCR();
}

/**
 * Event Listeners & Initialization
 */
document.addEventListener('DOMContentLoaded', () => {
  const calcBtn = document.getElementById('calcBtn');
  const resetBtn = document.getElementById('resetBtn');
  const calcForm = document.getElementById('calcForm');

  if (calcBtn) {
    calcBtn.addEventListener('click', calculateDSCR);
  }

  // Auto-calculate on input changes for instant responsiveness. 'change' as
  // well as 'input' so the checkbox and select both retrigger.
  const inputs = calcForm.querySelectorAll('input, select');
  inputs.forEach(input => {
    const handler = () => {
      const loan = parseFloat(document.getElementById('loan').value);
      const term = parseFloat(document.getElementById('term').value);
      if (loan > 0 && term > 0) {
        calculateDSCR();
      }
    };
    input.addEventListener('input', handler);
    input.addEventListener('change', handler);
  });

  // Preset Buttons
  const presetBtns = document.querySelectorAll('.btn-preset');
  presetBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const presetKey = e.target.getAttribute('data-preset');
      loadPreset(presetKey);
    });
  });

  // Reset Handler
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      setTimeout(() => {
        document.getElementById('dscrValue').textContent = '—';
        document.getElementById('dscrStatus').textContent = 'Enter property & financing figures to generate analysis';
        document.getElementById('statusBadge').className = 'badge badge-neutral';
        document.getElementById('statusBadge').textContent = 'Awaiting Calculation';
        document.getElementById('amortModePill').className = 'badge badge-neutral';
        document.getElementById('amortModePill').textContent = 'Amortizing';
        document.getElementById('noiValue').textContent = '$0.00';
        document.getElementById('tdsValue').textContent = '$0.00';
        document.getElementById('tdsLabel').textContent = 'Periodic Debt Service';
        document.getElementById('cashFlowValue').textContent = '$0.00';
        document.getElementById('annualDebtValue').textContent = '$0.00';
        document.getElementById('maxLoanValue').textContent = '$0.00';
        document.getElementById('resultsBanner').className = 'results-banner';
        document.getElementById('gaugeSubtitle').textContent = '1.25x is the conventional prime threshold';
        renderQualificationGauge(0, false);
      }, 50);
    });
  }

  // Mobile nav toggle
  const navToggle = document.getElementById('navToggle');
  const headerNav = document.getElementById('headerNav');
  if (navToggle && headerNav) {
    navToggle.addEventListener('click', () => {
      const isOpen = headerNav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', String(isOpen));
    });
    headerNav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        headerNav.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // Load default Case A on initial start
  loadPreset('caseA');
});
