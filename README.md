# Commodity-FX Transmission & Sovereign Risk Analyzer

**A Pipeline for Emerging Market Fixed-Income Stress Testing**

---

## 1. Executive Abstract

Emerging and frontier markets are highly vulnerable to global supply shocks. This project engineers a robust, end-to-end econometric architecture designed to mathematically map, isolate, and quantify exactly how a global commodity shock bleeds into domestic capital markets.

Moving beyond basic forecasting, this pipeline uses a **Structural Vector Autoregression (SVAR)** model to trace the exact timeline of the shock. It then translates that macroeconomic damage into a hard, dollar capital loss for a multi-period sovereign bond portfolio using second-order Taylor series approximations.

---

## 2. The Macroeconomic Transmission Framework (The Domino Effect)

Before writing the code, this pipeline was built on a rigorously defined macroeconomic theory of emerging market vulnerability. The transmission channel flows sequentially:

**Global Crude Shock $\rightarrow$ Terms of Trade Collapse $\rightarrow$ FX Depletion & Depreciation $\rightarrow$ Restrictive Monetary Policy $\rightarrow$ Sovereign Yield Spike $\rightarrow$ Bond Portfolio Capital Destruction**

1. **The Exogenous Shock:** A supply-side disruption causes global Brent Crude prices to spike.
2. **The Currency Drain:** Oil-importing emerging markets (like Kenya) must secure more US Dollars to cover escalating energy bills. This drains central bank foreign exchange reserves, triggering a depreciation of the local currency (USD/KES).
3. **The Yield Curve Repricing:** To defend the currency and combat imported inflation, the domestic central bank is forced to hike benchmark interest rates.
4. **The Fixed-Income Impact:** This aggressive monetary tightening forces domestic sovereign debt yields higher across the curve, crushing the value of existing fixed-income portfolios.

---

## 3. Data Architecture & Statistical Diagnostics

Time-series forecasting models break down if the underlying data is structurally flawed. Phase one of the engine enforces strict data hygiene.

### 3.1 Distribution Alignment & Normality Testing

Financial time series notoriously exhibit extreme price swings (kurtosis). The engine calculates the shape of the distributions and executes tests to ascertain normality. Passing this confirms that real-world tail risks are present, justifying the need for advanced risk modeling later on.

### 3.2 Dual-Stationarity Verification

Time-series models need data to be stable (stationary) over time. If a price is just wandering upward, the model might find a fake correlation. The engine converts raw prices into stable, continuous log returns.

To guarantee the data is safe to model, the pipeline uses a strict dual-verification matrix:

* **Augmented Dickey-Fuller (ADF):** Tests if the data is non-stationary.
* **Kwiatkowski-Phillips-Schmidt-Shin (KPSS):** Tests if the data is trend-stationary.

Only variables that mathematically pass *both* criteria are cleared for the core engine.

---

## 4. Structural Econometrics & SVAR Modeling

### 4.1 Directional Causality (The "Footprints" Test)

Correlation does not imply causation. Before building the model, the pipeline computes a **Granger Causality matrix**. This tests for timing it mathematically proves whether past oil prices help predict today's exchange rate better than the exchange rate's own history alone. It proves that oil moves first, validating the economic theory before modeling begins.

### 4.2 Reduced-Form VAR & Lag Optimization (The "Goldilocks" Score)

The core transmission mechanism is modeled using a Vector Autoregression (VAR) system, which analyzes how all the variables interact with each other over time.

* **AIC (Akaike Information Criterion):** The model uses AIC to decide how many months of history to look back. AIC rewards accuracy but penalizes complexity, finding the perfect balance so the model doesn't just overfit and memorize the past.
* **Durbin-Watson (The "Leftovers" Check):** After making predictions, the model checks its own errors using the Durbin-Watson statistic. It ensures the remaining errors are just random white noise and that no hidden trends were missed.

### 4.3 Structural Identification via Cholesky Decomposition (The "Who Punched First" Rule)

In financial markets, everything moves at once. If oil spikes and the currency crashes on the same day, a basic model gets confused about who caused what.

To fix this, the engine applies a **Cholesky decomposition** a mathematical filter that forces a strict timeline on the chaos. It enforces the reality that a global oil shock can crash the local currency instantly, but a local currency crash cannot instantly move the global price of oil. The forced causal order is:
**Brent Crude $\rightarrow$ USD/KES $\rightarrow$ Sovereign Spread**

---

## 5. Shock Transmission Dynamics

Once the model understands the structure of the economy, it extracts two critical metrics for institutional risk managers.

### 5.1 Orthogonalized Impulse Response Functions (The Shockwave Simulator)

The **OIRF** acts as a simulator. The model drops a massive, pure "+1 standard deviation" shock into Brent Crude and maps the exact month-by-month ripple effect hitting the currency and bond yields over the next year.

By tracking this, the engine calculates the **Pass-Through Half-Life** identifying the exact month where 50% of the total macroeconomic damage has been realized. This metric is vital for timing hedging operations.

### 5.2 Forecast Error Variance Decomposition (The Blame Pie Chart)

The **FEVD** breaks down future volatility into percentages. It answers a fundamental risk question: *At a 12-month horizon, exactly how much of a domestic bond portfolio's risk is driven by external global oil shocks versus local internal market noise?*

---

## 6. Non-Linear Portfolio Stress Testing

The final phase bridges the gap between macroeconomic statistics and fixed-income asset management. The engine simulates a $\$50,000,000$ stylized sovereign bond portfolio with weights across 2Y, 5Y, 10Y, and 30Y tenors.

Most basic financial analyses take a macro interest rate shock ($\Delta y$) and multiply it by duration to estimate bond price loss. That linear math severely overestimates capital destruction during extreme market shocks.

Instead, the fixed-income stress tester utilizes a second-order **Taylor Series Expansion** to accurately price the bonds, accounting for the natural curve of the price-yield relationship:

$$\frac{\Delta P}{P} \approx -D_{mod} \Delta y + \frac{1}{2} C (\Delta y)^2$$

* **Linear Duration Effect ($-D_{mod} \Delta y$):** The primary capital loss due to rising rates. As yields go up, bond prices go down.
* **Convexity Cushion ($\frac{1}{2} C (\Delta y)^2$):** The non-linear property of bonds that inherently acts as an organic brake, dampening the severity of the loss as rates surge.

By applying this non-linear pricing formula, the engine outputs the exact Mark-to-Market (MtM) terminal dollar drawdown across the aggregate fund.

---

## 🌐 Live Interactive Dashboards

*Hosted via GitHub Pages. Click to explore the full interactive Plotly suites:*

* **[1. Macroeconomic Shock Transmission Suite](https://pvvdrv.github.io/Commodity-Fx-Transmission_Analyzser/1_macro_transmission.html?utm_source=gemini)**
* **[2. 3D Yield Curve Volatility Surface](https://pvvdrv.github.io/Commodity-Fx-Transmission_Analyzser/2_yield_curve_surface.html?utm_source=gemini)**
* **[3. Dynamic Portfolio Stress Testing Suite](https://pvvdrv.github.io/Commodity-Fx-Transmission_Analyzser/3_portfolio_stress.html?utm_source=gemini)**

---

## 7. Deployment & Execution

The architecture is built entirely in Python, utilizing `pandas`, `numpy`, `statsmodels`, `scipy`, and `plotly`.

To deploy the pipeline, clone the repository and execute the main engine. The script will automatically compute the data ingestion, run the statistical proofs, fit the SVAR, execute the non-linear bond math, and launch the three interactive HTML dashboards locally in your default web browser.

```bash
git clone https://github.com/pvvdrv/Commodity-Fx-Transmission_Analyzser.git
cd Commodity-Fx-Transmission_Analyzser
pip install -r requirements.txt
python transmission_analyzer.py

```

---

## 8. Academic References

The econometric architecture and structural assumptions in this pipeline are grounded in the following literature:

* **Sims, C. A. (1980). *Macroeconomics and Reality*. Econometrica.**
*(The foundational paper that introduced Vector Autoregression and Impulse Response Functions to macroeconomic modeling).*
* **Granger, C. W. J. (1969). *Investigating Causal Relations by Econometric Models and Cross-spectral Methods*. Econometrica.**
*(The original framework for testing directional forecasting ability between time-series variables).*
* **Della Corte, P., Sarno, L., Schmeling, M., & Wagner, C. (2022). *Exchange Rates and Sovereign Risk*. Management Science.**
*(Empirical proof of the transmission mechanism utilized in this project, demonstrating that an increase in sovereign credit risk is accompanied by a significant depreciation of the domestic currency).*
