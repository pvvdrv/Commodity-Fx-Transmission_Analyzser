# Commodity-FX Transmission & Sovereign Risk Analyzer
**A Pipeline for Emerging Market Fixed-Income Stress Testing**



## 1. Executive Abstract

Emerging and frontier markets operate under chronic vulnerability to exogenous supply-side shocks. This project engineers a robust, end-to-end econometric architecture designed to mathematically map, isolate, and quantify the structural transmission of global commodity shocks into domestic capital markets. 

Moving beyond naive linear predictive algorithms, this pipeline leverages **Structural Vector Autoregression (SVAR)** with Cholesky causal ordering to model the exact transmission lag. It then translates that macroeconomic volatility into hard, non-linear Mark-to-Market (MtM) capital impact for a multi-tenor sovereign bond portfolio using second-order Taylor series approximations.

---

## 2. The Macroeconomic Transmission Framework

Before deploying the mathematical engine, the structural pipeline is built upon a rigorously defined macroeconomic theory of emerging market vulnerability. The modeled transmission channel flows sequentially:

**Global Crude Shock $\rightarrow$ Terms of Trade Collapse $\rightarrow$ FX Depletion & Depreciation $\rightarrow$ Restrictive Monetary Policy $\rightarrow$ Sovereign Yield Spike $\rightarrow$ Bond Portfolio Capital Destruction**

1. **The Exogenous Shock:** A supply-side disruption causes global Brent Crude prices to spike.
2. **The Currency Drain:** Oil-importing emerging markets (e.g., Kenya) must secure USD to cover escalating energy import bills. This severe terms-of-trade shock drains central bank foreign exchange reserves, triggering a structural depreciation of the local currency (USD/KES).
3. **The Yield Curve Repricing:** To defend the currency peg, prevent capital flight, and combat imported inflation, the domestic central bank is forced into a restrictive monetary posture (hiking the benchmark rate). 
4. **The Fixed-Income Impact:** This aggressive monetary tightening creates a violent upward repricing of domestic sovereign debt yields across the curve, executing severe capital destruction on existing fixed-income portfolios.

---

## 3. Data Architecture & Statistical Diagnostics

Time-series forecasting models deteriorate into spurious regressions if the underlying data is structurally flawed or non-stationary. Phase one of the engine enforces strict data hygiene.

### 3.1 Distribution Alignment & Normality Testing
Financial time series notoriously exhibit fat tails (leptokurtosis) and skewness. The engine calculates the third and fourth moments of the distributions and executes **Jarque-Bera tests** to ascertain normality. This dictates whether the subsequent models require robust standard errors.

### 3.2 Dual-Stationarity Verification
Vector Autoregressions require data to be $I(0)$ integrated. The engine transforms raw price levels into continuous log returns for global commodities and currencies, and absolute spread differences for yields. 

To guarantee stationarity without relying on a single test's assumptions, the pipeline utilizes a dual-verification matrix:
*   **Augmented Dickey-Fuller (ADF):** Tests the null hypothesis that a unit root is present (non-stationary). 
*   **Kwiatkowski-Phillips-Schmidt-Shin (KPSS):** Tests the inverse null hypothesis that the data is trend-stationary. 

Only variables that mathematically pass *both* criteria are cleared for the VAR engine.

---

## 4. Structural Econometrics & SVAR Modeling

### 4.1 Directional Causality (Granger Matrix)
Correlation does not imply causation. Before fitting the autoregressive system, the pipeline computes a Granger Causality matrix to statistically verify the directional flow of information. It tests and rejects the null hypothesis that Brent Crude returns do not forecast USD/KES depreciation, explicitly proving the macroeconomic theory using empirical F-tests prior to modeling.

### 4.2 Reduced-Form VAR & Lag Optimization
The core transmission mechanism is modeled using a Vector Autoregression system. The optimal lag structure ($p$) is dynamically selected via the **Akaike Information Criterion (AIC)** to balance model explanatory power against the penalty of overfitting:

$$Y_t = c + \sum_{i=1}^{p} A_i Y_{t-i} + u_t$$

Where $Y_t$ is a $k \times 1$ vector of endogenous variables, $c$ is the intercept, $A_i$ are coefficient matrices, and $u_t$ is the reduced-form error term. Post-estimation, the residuals ($u_t$) are subjected to **Durbin-Watson diagnostics** to ensure the absence of serial autocorrelation.

### 4.3 Structural Identification via Cholesky Decomposition
Because standard VAR residuals ($u_t$) are contemporaneously correlated, a shock to one variable cannot be isolated. To extract pure, uncorrelated structural shocks ($\varepsilon_t$), the engine applies a Cholesky decomposition:

$$u_t = B\varepsilon_t$$

**The Structural Hierarchy:** The $B$ matrix is lower-triangular, enforcing a strict recursive causal order: 
**Brent Crude $\rightarrow$ USD/KES $\rightarrow$ Sovereign Spread**

This mathematical constraint encodes economic reality into the matrix algebra: an exogenous shock to global oil prices instantaneously impacts the local shilling, but a shock to the local shilling cannot contemporaneously move the global price of Brent Crude.

---

## 5. Shock Transmission Dynamics

Once the SVAR model is fitted and structural identification is achieved, the engine extracts two critical metrics for institutional risk managers.

### 5.1 Orthogonalized Impulse Response Functions (OIRF)
The OIRF simulates a $+1\sigma$ structural shock to Brent Crude, tracking the dynamic, month-by-month response of the FX and Yield variables over a 12-month horizon. 

By accumulating these responses, the engine calculates the **Pass-Through Half-Life**—identifying the exact temporal node where 50% of the terminal macroeconomic damage has been realized. This metric is vital for timing hedging operations.

### 5.2 Forecast Error Variance Decomposition (FEVD)
The FEVD deconstructs the variance of the local currency and sovereign yields over time. It answers the fundamental risk question: *At a 6-month or 12-month horizon, what exact percentage of domestic market volatility is driven by global supply shocks versus internal domestic noise?*

---

## 6. Non-Linear Portfolio Stress Testing

The final phase bridges the gap between macroeconomic econometrics and fixed-income asset management. The engine simulates a $\$50,000,000$ stylized multi-tenor sovereign bond portfolio with explicit asset-liability weights across 2Y, 5Y, 10Y, and 30Y tenors.

When the SVAR model simulates a sovereign yield spike ($\Delta y$), the engine deliberately bypasses simple linear duration models. Linear duration assumes a straight-line relationship between yields and prices, which severely overestimates capital destruction during extreme tail-risk shocks. 

Instead, the fixed-income stress tester utilizes a second-order **Taylor Series Expansion** to accurately price the bonds, accounting for the curvature of the price-yield relationship:

$$\frac{\Delta P}{P} \approx -D_{mod} \Delta y + \frac{1}{2} C (\Delta y)^2$$

*   **Linear Duration Effect ($-D_{mod} \Delta y$):** The primary capital loss due to rising rates, dictated by the Modified Duration.
*   **Convexity Cushion ($\frac{1}{2} C (\Delta y)^2$):** The non-linear, second-derivative property of bonds that inherently cushions the severity of the loss as yields rise.

By applying this non-linear pricing formula across the weighted tenors, the engine outputs the exact Mark-to-Market (MtM) terminal dollar drawdown across the aggregate fund.

---

## 🌐 Live Interactive Dashboards
*Click the links below to instantly render the full interactive Plotly suites directly in your browser:*

* **[1. Macroeconomic Shock Transmission Suite](https://raw.githack.com/pwvdrv/Commodity-Fx-Transmission_Analyzser/main/1_macro_transmission.html)**
* **[2. 3D Yield Curve Volatility Surface](https://raw.githack.com/pwvdrv/Commodity-Fx-Transmission_Analyzser/main/2_yield_curve_surface.html)**
* **[3. Dynamic Portfolio Stress Testing Suite](https://raw.githack.com/pwvdrv/Commodity-Fx-Transmission_Analyzser/main/3_portfolio_stress.html)**

## 8. Deployment & Execution

The architecture is built entirely in Python, utilizing `pandas`, `numpy`, `statsmodels`, `scipy`, and `plotly`.

To deploy the pipeline, clone the repository and execute the main engine. The script will automatically compute the data ingestion, run the statistical proofs, fit the SVAR, execute the non-linear bond math, and launch the three interactive HTML dashboards locally in your default web browser.

```bash
  
git clone [https://github.com/pwvdrv/Commodity-FX-Transmission-Analyzer.git](https://github.com/pwvdrv/Commodity-FX-Transmission-Analyzer.git)
cd Commodity-FX-Transmission-Analyzer
pip install -r requirements.txt
python transmission_analyzer.py
