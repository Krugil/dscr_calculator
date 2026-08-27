function calc(gross, expenses, loan, rate, term, freq) {
  const paymentsPerYear = freq === 'monthly' ? 12 : 1;
  const periodicRate = (rate / 100) / paymentsPerYear;
  const totalPayments = term * paymentsPerYear;
  const denom = 1 - Math.pow(1 + periodicRate, -totalPayments);
  const payment = loan * periodicRate / denom;
  const NOI = gross - expenses;
  const DSCR = NOI / payment;
  return {payment, NOI, DSCR};
}
console.log(calc(10000, 3000, 200000, 5, 20, 'monthly'));
console.log(calc(8000, 2500, 150000, 4, 15, 'annual'));
console.log(calc(12500, 4000, 250000, 6, 25, 'monthly'));
