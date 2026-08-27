# Debt Service Coverage Ratio (DSCR) Calculator

A responsive, hyper-polished, static client-side **Debt Service Coverage Ratio (DSCR)** Calculator app for real estate investors, underwriters, and commercial mortgage borrowers.

Live Demo: Hosted on [GitHub Pages](https://krugil.github.io/dscr_calculator/)

---

## Formula & Definitions

$$\text{DSCR} = \frac{\text{Net Operating Income (NOI)}}{\text{Total Debt Service (TDS)}}$$

- **Net Operating Income (NOI)** = $\text{Gross Rental/Operating Income} - \text{Operating Expenses}$  
  *(Operating expenses exclude mortgage principal and interest).*
- **Total Debt Service (TDS)** = Total scheduled periodic loan payments (principal + interest) amortized over the loan term:
  $$P = \frac{L \cdot r}{1 - (1 + r)^{-n}}$$
  Where:
  - $L$ = Loan principal amount
  - $r$ = Periodic interest rate (Annual rate / payment frequency)
  - $n$ = Total scheduled payments (Loan term in years &times; payment frequency)

---

## Verified Test Cases

The application math has been verified against the following standard test cases:

1. **Case A (Standard Residential / Commercial Investment)**
   - Gross Income: $10,000 / month
   - Operating Expenses: $3,000 / month
   - Loan Amount: $200,000
   - Interest Rate: 5.0%
   - Amortization Term: 20 Years
   - Frequency: Monthly
   - **NOI:** $7,000.00
   - **Periodic TDS:** $1,319.91
   - **Expected DSCR:** **`5.30`**

2. **Case B (Annualized Debt Service / Low NOI)**
   - Gross Income: $8,000 / year
   - Operating Expenses: $2,500 / year
   - Loan Amount: $150,000
   - Interest Rate: 4.0%
   - Amortization Term: 15 Years
   - Frequency: Annual
   - **NOI:** $5,500.00
   - **Periodic TDS:** $13,491.17
   - **Expected DSCR:** **`0.41`**

3. **Case C (Long-Term Multifamily Asset)**
   - Gross Income: $12,500 / month
   - Operating Expenses: $4,000 / month
   - Loan Amount: $250,000
   - Interest Rate: 6.0%
   - Amortization Term: 25 Years
   - Frequency: Monthly
   - **NOI:** $8,500.00
   - **Periodic TDS:** $1,610.75
   - **Expected DSCR:** **`5.28`**

---

## Features

- **Instant Calculation Engine:** Live reactive updates as users enter loan and property parameters.
- **Visual Safety Meter & Health Badges:** Real-time feedback showing where the DSCR falls compared to standard lender thresholds (&ge; 1.25x).
- **SEO & AdSense Compatibility:** Clean meta tags, semantic HTML5 structure, non-intrusive standard ad placement slots, and educational industry benchmark guides.
- **100% Static & Zero-Dependency:** Pure HTML5, modern CSS3 variables, and vanilla ES6 JavaScript. Deployable anywhere with zero build pipeline.

---

## Assumptions & Known Limitations

- **Standard Amortization:** Calculates standard fully-amortizing fixed-rate loans.
- **Edge Cases:** Specialized structures such as interest-only introductory periods, balloon payment maturities, or blended portfolio-wide DSCR require customized loan schedules.
