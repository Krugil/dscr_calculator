// DSCR Calculator Core Engine

const presets = {
  caseA: { gross: 10000, expenses: 3000, loan: 200000, interest: 5, term: 20, frequency: 'monthly' },
  caseB: { gross: 8000, expenses: 2500, loan: 150000, interest: 4, term: 15, frequency: 'annual' },
  caseC: { gross: 12500, expenses: 4000, loan: 250000, interest: 6, term: 25, frequency: 'monthly' }
};

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
 * Format currency with commas and 2 decimals
 */
function formatCurrency(num) {
  if (isNaN(num) || !isFinite(num)) return '$0.00';
  return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

  if (loan <= 0 || termYears <= 0) {
    return;
  }

  const paymentsPerYear = frequency === 'monthly' ? 12 : 1;
  const totalPayments = termYears * paymentsPerYear;
  const periodicRate = periodicInterestRate(interest, frequency);
  
  // Total periodic debt service (TDS)
  const tds = computePeriodicPayment(loan, periodicRate, totalPayments);
  
  // Net Operating Income (NOI)
  const noi = gross - expenses;
  
  // DSCR calculation
  const dscr = tds > 0 ? (noi / tds) : 0;
  
  // Cash flow & annualized figures
  const netCashFlow = noi - tds;
  const annualizedTds = tds * paymentsPerYear;

  // DOM Elements
  const dscrValueEl = document.getElementById('dscrValue');
  const dscrStatusEl = document.getElementById('dscrStatus');
  const statusBadgeEl = document.getElementById('statusBadge');
  const noiValueEl = document.getElementById('noiValue');
  const tdsValueEl = document.getElementById('tdsValue');
  const tdsFreqTextEl = document.getElementById('tdsFreqText');
  const cashFlowValueEl = document.getElementById('cashFlowValue');
  const annualDebtValueEl = document.getElementById('annualDebtValue');
  const heroBox = document.querySelector('.dscr-hero-box');
  const meterPointer = document.getElementById('meterPointer');
  const meterPositionText = document.getElementById('meterPositionText');

  // Update Metric Text
  dscrValueEl.textContent = isFinite(dscr) ? dscr.toFixed(2) + 'x' : '—';
  noiValueEl.textContent = formatCurrency(noi);
  tdsValueEl.textContent = formatCurrency(tds);
  tdsFreqTextEl.textContent = frequency === 'monthly' ? 'Principal + Interest (Monthly)' : 'Principal + Interest (Annual)';
  cashFlowValueEl.textContent = formatCurrency(netCashFlow);
  annualDebtValueEl.textContent = formatCurrency(annualizedTds);

  // Status & Badge Evaluation
  heroBox.classList.remove('status-success', 'status-warning', 'status-danger');
  statusBadgeEl.className = 'badge';

  let meterPercent = 0;

  if (dscr < 1.0) {
    heroBox.classList.add('status-danger');
    statusBadgeEl.classList.add('badge-danger');
    statusBadgeEl.textContent = 'Negative Cash Flow';
    dscrStatusEl.textContent = 'High Default Risk: Operating income cannot cover debt obligations.';
    meterPositionText.textContent = `Current: ${dscr.toFixed(2)}x (Deficit)`;
    meterPercent = Math.max(2, (dscr / 1.0) * 35);
  } else if (dscr >= 1.0 && dscr < 1.25) {
    heroBox.classList.add('status-warning');
    statusBadgeEl.classList.add('badge-warning');
    statusBadgeEl.textContent = 'Marginal Coverage';
    dscrStatusEl.textContent = 'Tight Cash Cushion: Below conventional 1.25x prime lender benchmark.';
    meterPositionText.textContent = `Current: ${dscr.toFixed(2)}x (Marginal)`;
    meterPercent = 35 + ((dscr - 1.0) / 0.25) * 20;
  } else if (dscr >= 1.25 && dscr < 1.50) {
    heroBox.classList.add('status-success');
    statusBadgeEl.classList.add('badge-success');
    statusBadgeEl.textContent = 'Standard / Prime';
    dscrStatusEl.textContent = 'Healthy Coverage: Meets or exceeds standard commercial lender requirements.';
    meterPositionText.textContent = `Current: ${dscr.toFixed(2)}x (Qualified)`;
    meterPercent = 55 + ((dscr - 1.25) / 0.25) * 25;
  } else {
    heroBox.classList.add('status-success');
    statusBadgeEl.classList.add('badge-primary');
    statusBadgeEl.textContent = 'Strong / Low Risk';
    dscrStatusEl.textContent = 'Superior Cash Flow: Substantial income buffer over required debt service.';
    meterPositionText.textContent = `Current: ${dscr.toFixed(2)}x (Strong)`;
    const extra = Math.min(1.0, (dscr - 1.5) / 1.5);
    meterPercent = 80 + extra * 18;
  }

  meterPointer.style.left = `${Math.min(98, Math.max(2, meterPercent))}%`;
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

  // Auto-calculate on input changes for instant responsiveness
  const inputs = calcForm.querySelectorAll('input, select');
  inputs.forEach(input => {
    input.addEventListener('input', () => {
      const loan = parseFloat(document.getElementById('loan').value);
      const term = parseFloat(document.getElementById('term').value);
      if (loan > 0 && term > 0) {
        calculateDSCR();
      }
    });
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
        document.getElementById('noiValue').textContent = '$0.00';
        document.getElementById('tdsValue').textContent = '$0.00';
        document.getElementById('cashFlowValue').textContent = '$0.00';
        document.getElementById('annualDebtValue').textContent = '$0.00';
        document.querySelector('.dscr-hero-box').className = 'dscr-hero-box';
        document.getElementById('meterPointer').style.left = '0%';
        document.getElementById('meterPositionText').textContent = 'Threshold: 1.25x';
      }, 50);
    });
  }

  // Load default Case A on initial start
  loadPreset('caseA');
});
