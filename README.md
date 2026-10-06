# Commodity-FX Transmission & Sovereign Risk Analyzer

[![Live Dashboard](https://img.shields.io/badge/View-Live_Interactive_Dashboard-2ea44f?style=for-the-badge)](https://pvvdrv.github.io/Commodity-Fx-Transmission_Analyzser/risk_analyzer_dashboard.html)

**[Click Here to Access the Live Interactive Dashboard](https://pvvdrv.github.io/Commodity-Fx-Transmission_Analyzser/risk_analyzer_dashboard.html)**

## Overview
This quantitative engine models the transmission mechanism of global commodity shocks (specifically crude oil) to emerging market foreign exchange rates and sovereign debt pricing. Built with Python, it utilizes time-series econometrics and fixed-income analytics to quantify how external macroeconomic shocks dictate localized borrowing costs and portfolio tail-risk.

The current implementation acts as a stress-testing pipeline for the **Kenya 10-Year Government Bond**, analyzing its vulnerability to the USD/KES exchange rate, global risk appetite (S&P 500), and US monetary policy (US 10-Year Treasury Yields).

---

## Methodology & Mathematical Framework

The pipeline is divided into four primary quantitative modules:

### 1. Data Preprocessing & The Illiquidity Filter
Emerging market debt frequently suffers from zero-volume trading days, resulting in flatlined, "stale" pricing data. Feeding raw stale data into a statistical model causes it to falsely interpret illiquidity as "zero risk." 
To correct this, the engine applies a dual-filter:
* **Cubic Spline Interpolation:** Missing or stale data points are replaced with mathematically inferred values using a 3rd-order polynomial curve.
* **Rolling Moving Average:** A 3-day trailing window is applied to smooth out the jagged micro-volatility inherent to thin emerging markets, preparing a continuous series for differencing.
* **Stationarity Testing:** The Augmented Dickey-Fuller (ADF) test is applied to ensure all price levels are transformed into stationary returns/basis-point diffs before entering the VAR matrix.

### 2. Time-Series Econometrics (VAR)
The core transmission mechanism is captured using a Vector Autoregression (VAR) framework. The optimal lag length is dynamically selected using the Akaike Information Criterion (AIC). 
The generic VAR($p$) process is defined as:

$$Y_t = c + A_1 Y_{t-1} + A_2 Y_{t-2} + \dots + A_p Y_{t-p} + e_t$$

Where $Y_t$ is the vector of our 5 endogenous variables: (1) Oil Returns, (2) S&P 500 Returns, (3) US 10Y Yield Shifts, (4) USD/KES Returns, and (5) Local Sovereign Yield Shifts.
* **Impulse Response Functions (IRF):** Traces the dynamic 10-day marginal impact of a 1 standard deviation shock to oil prices on local FX and bond yields.
* **Forecast Error Variance Decomposition (FEVD):** Quantifies the exact percentage of sovereign yield variance attributable to the other macro variables over the forecast horizon.

### 3. Fixed Income Risk Pricing
To translate theoretical yield shocks into actual monetary damage, the engine calculates the bond's Macaulay Duration, Modified Duration ($D_{mod}$), and Convexity ($C$) based on its explicit semi-annual cash flows. 

Price shocks are estimated using a second-order Taylor series expansion to capture the bond's non-linear price-yield relationship:

$$\frac{\Delta P}{P} \approx -D_{mod} \cdot \Delta y + \frac{1}{2} C \cdot (\Delta y)^2$$

### 4. Portfolio Tail-Risk Modeling
The engine conducts extreme-value stress testing on a simulated $100M baseline portfolio.
* **Value-at-Risk (VaR):** Calculates the maximum expected portfolio loss over a 1-day horizon at a 99% confidence interval based on historical yield volatility.
* **Conditional VaR (Expected Shortfall):** Quantifies the expected average loss in the absolute worst-case scenarios that exceed the VaR threshold.

---

## Model Upgrades, Assumptions & Known Weaknesses

* **Omitted Variable Bias Resolved:** The model integrates FRED API data (S&P 500 and US 10-Year Treasury) to serve as proxies for global risk appetite and liquidity. This expands the VAR matrix, ensuring the model does not falsely blame oil prices for bond sell-offs actually caused by US Federal Reserve rate hikes or broader stock market panics.
* **The Linearity Assumption (No GARCH Overlay):** The current VAR framework assumes homoskedasticity (constant volatility). It currently lacks a GARCH (Generalized Autoregressive Conditional Heteroskedasticity) overlay. Consequently, it calculates a 2% oil drop during a calm market using the exact same statistical weight as a 2% drop during a severe financial crisis.
* **Data Ingestion Risks:** While the model uses the robust FRED API for macro data, it relies on Yahoo Finance for commodity and FX pairs. A fallback synthesis generator is built-in to prevent pipeline crashes during web-scraping blackouts, but for enterprise deployment, this should be routed through a dedicated institutional feed (e.g., Bloomberg B-PIPE or Refinitiv).

---

## Setup & Local Execution

**Prerequisites:**
You will need a free API key from the Federal Reserve Economic Data (FRED) portal. 

**Installation:**
```bash
git clone [https://github.com/pvvdrv/Commodity-Fx-Transmission_Analyzser.git](https://github.com/pvvdrv/Commodity-Fx-Transmission_Analyzser.git)
cd Commodity-Fx-Transmission_Analyzser
pip install -r requirements.txt
