# DSCR Calculator

This is an all‑static Debt Service Coverage Ratio calculator.

## Usage
1. Open `index.html` in a browser.
2. Enter the required numbers:
   - **Gross rental/operating income**
   - **Operating expenses** (excluding debt service)
   - **Loan amount**
   - **Annual interest rate (%)**
   - **Loan term (years)**
   - **Payment frequency** (Monthly or Annual)
3. Click **Calculate** to see:
   - Periodic debt payment (TDS)
   - Net Operating Income (NOI)
   - DSCR value

## Test Cases
1. **Case A**
   - Gross: $10,000
   - Expenses: $3,000
   - Loan: $200,000
   - Interest: 5%
   - Term: 20 years
   - Frequency: Monthly
   - Expected DSCR ≈ 5.30

2. **Case B**
   - Gross: $8,000
   - Expenses: $2,500
   - Loan: $150,000
   - Interest: 4%
   - Term: 15 years
   - Frequency: Annual
   - Expected DSCR ≈ 0.41

3. **Case C**
   - Gross: $12,500
   - Expenses: $4,000
   - Loan: $250,000
   - Interest: 6%
   - Term: 25 years
   - Frequency: Monthly
   - Expected DSCR ≈ 5.28

> **Known limitations**
> - Interest‑only periods are not handled.
> - Balloon payments are not supported.
> - Multi‑property calculations are beyond the scope of this tool.
> 
> These edge cases are *escalated* to the user for clarifications.
