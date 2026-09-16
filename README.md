# Commodity-FX Transmission & Bond Risk Analyzer

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Statsmodels](https://img.shields.io/badge/Statsmodels-Econometrics-darkgreen)
![Plotly](https://img.shields.io/badge/Plotly-Interactive_Viz-purple)
![Risk](https://img.shields.io/badge/Risk-Fixed_Income-red)

An institutional-grade quantitative pipeline modeling the transmission of global commodity supply shocks into local FX depreciation and subsequent sovereign fixed-income portfolio drawdowns. 

Moving beyond standard predictive algorithms, this project leverages structural econometrics to prove causality, map transmission lag, and translate macroeconomic volatility into non-linear Mark-to-Market (MtM) capital impact.

## 📊 Interactive Dashboards & Analytics

*(Note: Click to view full interactive surfaces)*

### 1. Macroeconomic Shock Transmission & Elasticity
![Macro Dashboard](macro_dashboard.png)
*Tracking a $+1\sigma$ Brent Crude shock through USD/KES depreciation and Sovereign Spread widening over a 12-month horizon.*

### 2. 3D Yield Curve Volatility Surface
![3D Surface](3d_surface.png)
*Time-horizon vs. Bond Tenor vs. Simulated Yield Shock mapping the curve flattening/steepening dynamics.*

### 3. Non-Linear Portfolio Stress Testing ($50M AUM)
![Stress Test](stress_test.png)
*Aggregate and tranche-level fund drawdowns incorporating convexity cushions across the yield curve.*

---

## 📐 Quantitative Methodology

The analytical engine is built on a strict, mathematically sound pipeline to ensure institutional reliability.

### I. Dual-Stationarity & Structural Identification
To prevent spurious regressions, the pipeline enforces $I(0)$ integration using continuous log returns and absolute spread differences, validated via both **Augmented Dickey-Fuller (ADF)** and **KPSS** unit root tests.

Directional causality is proven prior to modeling using a **Granger Causality Matrix**, statistically verifying that global oil shocks drive emerging market FX, not vice versa.

### II. Cholesky-Ordered Vector Autoregression (VAR)
The transmission mechanism is modeled using a structural VAR system optimized via the Akaike Information Criterion (AIC). 

$$Y_t = c + A_1 Y_{t-1} + \dots + A_p Y_{t-p} + u_t$$

Crucially, the system enforces a strict recursive causal structure (Cholesky Decomposition) on the reduced-form errors to identify the structural shocks $\varepsilon_t$:

$$u_t = B \varepsilon_t$$

The imposed hierarchy ($Brent \rightarrow USD/KES \rightarrow Yields$) mathematically prevents local domestic debt from contemporaneously affecting global crude prices.

### III. Fixed-Income Non-Linear Pricing
To translate the simulated yield shocks ($\Delta y$) into capital drawdowns for a stylized $\$50M$ multi-tenor sovereign book, the engine bypasses simple linear duration and utilizes a second-order Taylor expansion to account for the convexity cushion:

$$\frac{\Delta P}{P} \approx -D_{mod} \cdot \Delta y + \frac{1}{2} C \cdot (\Delta y)^2$$

Where $D_{mod}$ is Modified Duration and $C$ is Convexity, applied uniquely across the 2Y, 5Y, 10Y, and 30Y tenors.

---

## ⚙️ System Architecture

1. **`DataIngestion`**: Multi-threaded market synchronization (Brent Crude, USD/KES, EM Sovereign Proxy).
2. **`StationarityEngine`**: Statistical validation (Skew, Kurtosis, Jarque-Bera, ADF, KPSS).
3. **`VAREngine`**: Durbin-Watson tested, Cholesky-ordered structural mapping.
4. **`TransmissionDynamicsEngine`**: Orthogonalized Impulse Response Functions (OIRF) and Forecast Error Variance Decomposition (FEVD).
5. **`FixedIncomeStressTester`**: ALM-weighted non-linear duration/convexity capital shock processing.
6. **`VisualizerDashboard`**: Auto-deployed Plotly HTML suite.

## 🚀 Execution

Clone the repository and run the engine. The script will automatically compute the pipeline and launch the three interactive HTML dashboards in your local web browser.

```bash
git clone [https://github.com/pwvdrv/Commodity-FX-Transmission-Analyzer.git](https://github.com/pwvdrv/Commodity-FX-Transmission-Analyzer.git)
cd Commodity-FX-Transmission-Analyzer
pip install -r requirements.txt
python transmission_analyzer.py
