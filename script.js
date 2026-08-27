document.getElementById('dscr-form').addEventListener('submit', function(e) {
  e.preventDefault();

  const gross = parseFloat(document.getElementById('grossIncome').value);
  const expenses = parseFloat(document.getElementById('operatingExpenses').value);
  const loan = parseFloat(document.getElementById('loanAmount').value);
  const rate = parseFloat(document.getElementById('interestRate').value);
  const term = parseInt(document.getElementById('termYears').value, 10);
  const freq = document.getElementById('paymentFreq').value;

  if ([gross, expenses, loan, rate, term].some(v => isNaN(v) || v <= 0)) {
    alert('All inputs must be positive numbers');
    return;
  }

  const paymentsPerYear = freq === 'monthly' ? 12 : 1;
  const periodicRate = (rate / 100) / paymentsPerYear;
  const totalPayments = term * paymentsPerYear;

  // Standard amortization formula for PMT
  const denom = 1 - Math.pow(1 + periodicRate, -totalPayments);
  const payment = loan * periodicRate / denom; // TDS

  const NOI = gross - expenses;

  if (payment <= 0) {
    document.getElementById('result').innerHTML = '<p>Error: Periodic debt payment must be > 0.</p>';
    return;
  }

  const DSCR = NOI / payment;

  document.getElementById('result').innerHTML = `<p>Periodic Debt Payment (TDS): $${payment.toFixed(2)}</p>
  <p>Net Operating Income (NOI): $${NOI.toFixed(2)}</p>
  <p>DSCR: ${DSCR.toFixed(2)}</p>`;
});