// Helper to convert annual rate to periodic rate
function periodicInterestRate(annualRate, frequency) {
  const rate = annualRate / 100;
  if (frequency === 'monthly') return rate / 12;
  return rate; // annual
}
// Helper to calculate payment using amortization formula
function computePayment(loan, rate, nPayments) {
  if (rate === 0) return loan / nPayments;
  const factor = Math.pow(1 + rate, nPayments);
  return (loan * rate * factor) / (factor - 1);
}
function calculateDSCR() {
  const gross = parseFloat(document.getElementById('gross').value) || 0;
  const expenses = parseFloat(document.getElementById('expenses').value) || 0;
  const loan = parseFloat(document.getElementById('loan').value) || 0;
  const interest = parseFloat(document.getElementById('interest').value) || 0;
  const termYears = parseFloat(document.getElementById('term').value) || 0;
  const frequency = document.getElementById('frequency').value;
  const nPayments = frequency === 'monthly' ? termYears * 12 : termYears;
  const rate = periodicInterestRate(interest, frequency);
  const payment = computePayment(loan, rate, nPayments);
  const NOI = gross - expenses;
  const DSCR = NOI / payment;
  const resultsDiv = document.getElementById('results');
  resultsDiv.innerHTML = `
    <p><strong>Net Operating Income (NOI):</strong> $${NOI.toFixed(2)}</p>
    <p><strong>Periodic Debt Payment (TDS):</strong> $${payment.toFixed(2)}</p>
    <p><strong>DSCR:</strong> ${DSCR.toFixed(2)}</p>
  `;
}

document.getElementById('calcBtn').addEventListener('click', calculateDSCR);
