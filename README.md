# Commodity-FX Transmission & Sovereign Risk Analyzer

**[Click Here to Access the Live Interactive Dashboard](https://pvvdrv.github.io/Commodity-Fx-Transmission_Analyzser/risk_analyzer_dashboard.html)**

---

## 1. What This Project Does

Investing in emerging market government bonds is highly unpredictable. When a global event happens—like crude oil prices suddenly skyrocketing—it sets off a dangerous chain reaction. Net-importing countries bleed cash to buy expensive oil, their local currency crashes, and their central banks are forced to hike interest rates to stop the bleeding. When interest rates go up, the value of existing government bonds crashes. 

Instead of relying on guesswork or economic theories to predict how bad the damage will be, this project builds a systematic, mathematical engine. It pulls live global market data, calculates exactly how fast an oil shock ripples through the local economy, and determines the exact dollar-value loss for a simulated **$100 Million portfolio** holding the Kenya 10-Year Government Bond.

---

## 2. The Economic Variables We Track

To accurately map this chain reaction, the model pulls data from the Federal Reserve Economic Data (FRED) API and Yahoo Finance to track five specific forces:

### 1. Global Risk Appetite — S&P 500 (`^GSPC`)
* **What it measures:** The performance of the largest 500 companies in the US.
* **Why we use it:** We need to know if investors are feeling brave or panicked. If Kenyan bonds crash, we use this to prove whether it was caused by an oil shock, or if it was just a day when the entire global stock market was panicking.

### 2. Global Liquidity — US 10-Year Treasury Yield (`DGS10`)
* **What it measures:** The borrowing cost for the United States government.
* **Why we use it:** The US Treasury is the safest asset in the world. When US interest rates go up, global investors pull their money out of risky emerging markets and put it into safe US bonds. Tracking this prevents us from falsely blaming oil for a bond crash that was actually caused by the US Federal Reserve.

### 3. The Catalyst — Crude Oil Futures (`CL=F`)
* **What it measures:** The global price of energy.
* **Why we use it:** For emerging markets that import their fuel, a spike in oil prices acts like a massive, immediate tax on the entire country, draining foreign currency reserves.

### 4. Local Currency — US Dollar to Kenyan Shilling (`KES=X`)
* **What it measures:** How many shillings it takes to buy one US Dollar.
* **Why we use it:** This is the bridge between global shocks and local pain. A weakening currency means imported goods (like fuel and food) become instantly more expensive, triggering inflation.

### 5. Local Borrowing Costs — Kenya 10-Year Sovereign Yield
* **What it measures:** The interest rate the Kenyan government must pay to borrow money for a decade.
* **Why we use it:** This is our target variable. As this yield goes up, the value of our $100M bond portfolio goes down. 

---

## 3. How We Process the Data (The Logic & Math)

Financial data from emerging markets is notoriously messy. Here is how the engine cleans the data and calculates the risk:

### Step 1: The Illiquidity Filter (Fixing Stale Data)
In the US, bonds trade thousands of times a second. In emerging markets, a bond might not trade at all on a Tuesday or Wednesday. If we feed that raw data into a model, the computer will see "0% change" and falsely assume there is "zero risk." 
To fix this, we use **Cubic Spline Interpolation** to mathematically draw a curve over the missing days, and a **3-Day Moving Average** to smooth out the jagged noise. This gives the algorithm a clean, logical trendline to read.

### Step 2: Tracking the Chain Reaction (Vector Autoregression)
To see how our five variables interact, we use a statistical model called Vector Autoregression (VAR). Instead of just looking at how A affects B, VAR looks at how A affects B, while B is simultaneously affecting C, and C is affecting A. 

$$Y_t = c + A_1 Y_{t-1} + A_2 Y_{t-2} + \dots + A_p Y_{t-p} + e_t$$

We use this math to simulate a sudden 1-standard-deviation spike in oil prices and track exactly how many days it takes for the local currency and bond yields to react.

### Step 3: Calculating the Damage (Bond Convexity)
Once the VAR model tells us how much interest rates will rise, we need to price the damage. Because bond prices and yields move on a curve (not a straight line), we use a Taylor series expansion formula that accounts for **Modified Duration** and **Convexity**:

$$\frac{\Delta P}{P} \approx -D_{mod} \cdot \Delta y + \frac{1}{2} C \cdot (\Delta y)^2$$

### Step 4: Stress Testing the Portfolio (Value-at-Risk)
Finally, the model calculates **Value-at-Risk (VaR)** and **Conditional VaR (CVaR)** at a 99% confidence level. 
* **VaR** tells us: "On 99 out of 100 normal trading days, the portfolio will not lose more than $X."
* **CVaR** tells us: "On that 1 absolute worst, disastrous day, here is the average amount of cash we should expect to lose."

---

## 4. The Interactive Dashboard (What You See)

The Python script automatically generates a 4-panel HTML dashboard to visualize the math. Here is how to read the output:

| Chart | What it Tracks | How to Interpret It |
| :--- | :--- | :--- |
| **(A) Asset Dynamics** | Oil vs. US Markets vs. Local Currency | If the blue line (Oil) spikes and the orange line (Currency) rises shortly after, it proves expensive oil is draining the local economy's value. |
| **(B) Shock Transmission** | The 10-day domino effect of an oil shock | If the red line (Bond Yields) dips below zero, it means an oil shock caused local borrowing costs to drop immediately and settle at a "new normal." |
| **(C) Variance Breakdown** | The exact causes of bond volatility | The grey area is normal, random market noise. The colored blocks explicitly quantify how much of the bond's movement is caused by the US Dollar, Oil, or the S&P 500. |
| **(D) Convexity Pricing** | Portfolio losses during a market crash | The red line curves away from the straight dashed line. This "convexity cushion" proves your actual cash losses will be slightly *less* severe than what basic, straight-line math predicts. |

---

## 5. Backtest Results & What We Learned

Based on the most recent data run for the Kenyan market, the model revealed several critical, counter-intuitive insights:

1. **Currency is the True Driver:** The Variance Breakdown (Chart C) proved that direct contagion from global oil and US stock markets plays a surprisingly small visual role in daily Kenyan bond volatility. Instead, **local currency fluctuations (USD/KES) and internal market noise are the overwhelming drivers** of local borrowing costs. 
2. **Counter-Intuitive Shock Responses:** Traditional economic theory says expensive oil causes inflation, which causes interest rates to rise. However, the simulation (Chart B) showed that in this specific historical window, a sudden jump in oil prices actually caused local borrowing costs to *drop* immediately, highlighting the complex realities of frontier market liquidity.
3. **The Convexity Cushion is Real:** Stress testing the $100M portfolio demonstrated that using basic linear math (Duration) heavily overestimates portfolio losses during severe market crashes. The bond's non-linear "Convexity" acts as a mathematical shock absorber, saving the portfolio from expected extreme losses (Chart D).

---

## 6. Model Limitations & How to Fix Them

No quantitative model is perfect. Here are the current blind spots in this engine and how they can be upgraded in future versions:

* **Limitation 1: The "Constant Panic" Assumption (Linearity)**
  * **The Problem:** The current math assumes markets are equally calm or crazy all the time. It treats a 2% oil drop during a boring Tuesday exactly the same as a 2% drop during a severe global financial crisis. 
  * **The Fix:** Layering a GARCH (Generalized Autoregressive Conditional Heteroskedasticity) model over the math. GARCH acts like a "panic sensor," telling the algorithm to weigh shocks differently depending on the current level of global fear.
* **Limitation 2: Free Data Pipelines**
  * **The Problem:** While the US macro data comes from a solid source (FRED), the script relies on Yahoo Finance for oil and currency prices. Free web scrapers occasionally break or miss data points.
  * **The Fix:** Connect the Python script directly to a paid, institutional-grade API like Bloomberg, Refinitiv, or a dedicated algorithmic trading data feed for flawless reliability. 
* **Limitation 3: The Single-Country Focus**
  * **The Problem:** This model only looks at Kenya in a vacuum. In the real world, if Kenyan bonds crash, investors might panic and sell neighboring country bonds too (a contagion effect).
  * **The Fix:** Upgrade the math to a "Panel VAR." This allows the engine to track multiple Sub-Saharan African economies at the exact same time, measuring how a shock in one country spills over into another.

---

## 7. How the Code is Structured

The project is built using a clean, Object-Oriented structure in Python:

```text
Commodity-Fx-Transmission_Analyzser/
│
├── Commodity_FX_Transmission_Analyzer.py  # Main Python script (Data ingestion, math, and HTML generation)
├── risk_analyzer_dashboard.html           # Generated interactive dashboard 
├── requirements.txt                       # List of required Python libraries
└── README.md                              # Project documentation and analysis
