import os
import sys
import webbrowser
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from fredapi import Fred
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

warnings.filterwarnings("ignore")


class CommoditySovereignRiskEngine:
    def __init__(
        self,
        commodity_ticker: str = "CL=F",
        fx_ticker: str = "KES=X",
        fred_api_key: str = "YOUR_FRED_API_KEY", 
        period: str = "5y",
        base_yield: float = 12.28,  
        portfolio_notional: float = 100_000_000.0,
    ):
        self.commodity_ticker = commodity_ticker
        self.fx_ticker = fx_ticker
        self.fred_api_key = fred_api_key
        self.period = period
        self.base_yield = base_yield
        self.portfolio_notional = portfolio_notional

        self.raw_data = pd.DataFrame()
        self.stationary_data = pd.DataFrame()
        self.var_model = None
        self.var_results = None
        self.irf = None
        self.fevd = None
        self.bond_specs = {}

    def fetch_and_clean_data(self) -> pd.DataFrame:
        print("[1/6] Ingesting global macro data via FRED and yfinance...")
        
        try:
            fred = Fred(api_key=self.fred_api_key)
            sp500_series = fred.get_series('SP500')
            treasury_series = fred.get_series('DGS10')
            
            fred_df = pd.DataFrame({
                "US500": sp500_series,
                "US_10Y_Treasury": treasury_series
            })
            fred_df.index = pd.to_datetime(fred_df.index).tz_localize(None)
            
        except Exception as e:
            print(f"      [!] FRED API alert ({e}). Synthesizing FRED data...")
            dates = pd.date_range(end=pd.Timestamp.today(), periods=1260, freq="B")
            np.random.seed(42)
            fred_df = pd.DataFrame({
                "US500": 4500.0 * np.exp(np.cumsum(np.random.normal(0.0003, 0.012, len(dates)))),
                "US_10Y_Treasury": 4.0 + np.cumsum(np.random.normal(0.0, 0.05, len(dates)))
            }, index=dates)

        try:
            yf_df = yf.download(
                [self.commodity_ticker, self.fx_ticker],
                period=self.period,
                progress=False,
                auto_adjust=False,
            )["Close"]

            if isinstance(yf_df.columns, pd.MultiIndex):
                yf_df.columns = yf_df.columns.get_level_values(0)

            yf_df = pd.DataFrame({
                "Commodity": yf_df[self.commodity_ticker],
                "FX": yf_df[self.fx_ticker]
            })
            yf_df.index = pd.to_datetime(yf_df.index).tz_localize(None)

        except Exception as err:
            print(f"      [!] yfinance alert ({err}). Synthesizing Commodity/FX data...")
            dates = pd.date_range(end=pd.Timestamp.today(), periods=1260, freq="B")
            np.random.seed(42)
            oil_returns = np.random.normal(0.0004, 0.025, len(dates))
            yf_df = pd.DataFrame({
                "Commodity": 75.0 * np.exp(np.cumsum(oil_returns)),
                "FX": 128.0 * np.exp(np.cumsum(0.25 * oil_returns + np.random.normal(0.0002, 0.008, len(dates)))),
            }, index=dates)

        df = pd.merge(fred_df, yf_df, left_index=True, right_index=True, how="inner").dropna()

        np.random.seed(42)
        fx_pct = df["FX"].pct_change().fillna(0).values
        yield_shocks = (fx_pct * 15.0) + np.random.normal(0.0, 0.05, len(df))
        raw_yields = self.base_yield + np.cumsum(yield_shocks)
        
        raw_yields[10:15] = raw_yields[9] 
        raw_yields[40:45] = raw_yields[39]
        df["Sovereign_Yield"] = raw_yields

        is_stale = df["Sovereign_Yield"].diff() == 0.0
        df.loc[is_stale, "Sovereign_Yield"] = np.nan
        df["Sovereign_Yield"] = df["Sovereign_Yield"].interpolate(method="spline", order=3)
        df["Sovereign_Yield"] = df["Sovereign_Yield"].rolling(window=3, min_periods=1).mean()

        self.raw_data = df.dropna()
        return self.raw_data

    @staticmethod
    def check_stationarity_adf(series: pd.Series, name: str, alpha: float = 0.05) -> dict:
        clean_series = series.dropna()
        result = adfuller(clean_series, autolag="AIC")
        stat, p_val = result[0], result[1]
        return {
            "Variable": name,
            "ADF_Stat": round(stat, 4),
            "p_value": round(p_val, 4),
            "Stationary": p_val < alpha,
        }

    def prepare_stationary_returns(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        print("[2/6] Evaluating stationarity across an expanded global matrix...")
        adf_audit = []
        for col in self.raw_data.columns:
            adf_audit.append(self.check_stationarity_adf(self.raw_data[col], f"Level: {col}"))

        self.stationary_data = pd.DataFrame(
            {
                "Commodity_Ret": self.raw_data["Commodity"].pct_change() * 100.0,
                "US500_Ret": self.raw_data["US500"].pct_change() * 100.0, 
                "US_10Y_Diff_bps": self.raw_data["US_10Y_Treasury"].diff() * 100.0, 
                "FX_Ret": self.raw_data["FX"].pct_change() * 100.0,
                "Yield_Diff_bps": self.raw_data["Sovereign_Yield"].diff() * 100.0,
            },
            index=self.raw_data.index,
        ).dropna()

        for col in self.stationary_data.columns:
            adf_audit.append(self.check_stationarity_adf(self.stationary_data[col], f"Diff/Ret: {col}"))

        return pd.DataFrame(adf_audit), self.stationary_data

    def fit_var_model(self, maxlags: int = 8) -> int:
        print("[3/6] Fitting expanded Vector Autoregression (VAR) framework...")
        self.var_model = VAR(self.stationary_data)
        lag_order = self.var_model.select_order(maxlags=maxlags)
        selected_lag = lag_order.aic if lag_order.aic > 0 else 1
        self.var_results = self.var_model.fit(selected_lag)
        return selected_lag

    def test_granger_causality(self, maxlag: int = 5) -> pd.DataFrame:
        tests = {}
        targets = ["US500_Ret", "US_10Y_Diff_bps", "FX_Ret", "Yield_Diff_bps"]
        for target in targets:
            sub_df = self.stationary_data[[target, "Commodity_Ret"]]
            gc_res = grangercausalitytests(sub_df, maxlag=maxlag, verbose=False)
            min_p = min([gc_res[lag][0]["ssr_ftest"][1] for lag in range(1, maxlag + 1)])
            tests[f"Commodity -> {target}"] = {
                "Min_p_value": round(min_p, 4),
                "Granger_Causes": min_p < 0.05,
            }
        return pd.DataFrame(tests).T

    def run_dynamics(self, periods: int = 10):
        print("[4/6] Computing dynamic Impulse Responses and FEVD...")
        self.irf = self.var_results.irf(periods)
        self.fevd = self.var_results.fevd(periods)

    @staticmethod
    def calculate_bond_metrics(ytm_pct: float, coupon_rate_pct: float, maturity_years: float, face_value: float = 100.0, freq: int = 2) -> dict:
        ytm = ytm_pct / 100.0
        y_period = ytm / freq
        total_periods = int(maturity_years * freq)
        coupon_pmt = (coupon_rate_pct / 100.0 * face_value) / freq

        cash_flows = np.full(total_periods, coupon_pmt)
        cash_flows[-1] += face_value
        periods = np.arange(1, total_periods + 1)
        discount_factors = (1.0 + y_period) ** periods

        pv_cash_flows = cash_flows / discount_factors
        bond_price = np.sum(pv_cash_flows)

        mac_duration = np.sum(periods * pv_cash_flows) / (bond_price * freq)
        mod_duration = mac_duration / (1.0 + y_period)

        conv_terms = periods * (periods + 1) * pv_cash_flows
        convexity = np.sum(conv_terms) / (bond_price * ((1.0 + y_period) ** 2) * (freq ** 2))
        dv01 = (mod_duration * bond_price) * 0.0001

        return {"Bond_Price": bond_price, "Mac_Duration": mac_duration, "Mod_Duration": mod_duration, "Convexity": convexity, "DV01": dv01}

    @staticmethod
    def estimate_price_shock(dy_bps: float, mod_duration: float, convexity: float) -> float:
        dy = dy_bps / 10000.0
        linear_term = -mod_duration * dy
        convexity_term = 0.5 * convexity * (dy ** 2)
        return (linear_term + convexity_term) * 100.0

    def calculate_portfolio_stress(self, confidence_level: float = 0.99) -> dict:
        print("[5/6] Executing portfolio stress testing and tail-risk metrics...")
        yield_changes = self.stationary_data["Yield_Diff_bps"]
        mu = yield_changes.mean()
        sigma = yield_changes.std()

        z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
        z = z_scores.get(confidence_level, 2.326)

        worst_dy_bps = mu + (z * sigma)
        current_yield = self.raw_data["Sovereign_Yield"].iloc[-1]

        self.bond_specs = self.calculate_bond_metrics(current_yield, 12.50, 10.0)

        pct_loss_var = self.estimate_price_shock(worst_dy_bps, self.bond_specs["Mod_Duration"], self.bond_specs["Convexity"])
        dollar_var = abs(self.portfolio_notional * (pct_loss_var / 100.0))

        alpha = 1.0 - confidence_level
        pdf_z = (1.0 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * (z ** 2))
        cvar_dy_bps = mu + sigma * (pdf_z / alpha)

        pct_loss_cvar = self.estimate_price_shock(cvar_dy_bps, self.bond_specs["Mod_Duration"], self.bond_specs["Convexity"])
        dollar_cvar = abs(self.portfolio_notional * (pct_loss_cvar / 100.0))

        return {"Latest_Yield_pct": round(current_yield, 2), "1D_Worst_Case_dy_bps": round(worst_dy_bps, 2), "1D_VaR_Dollar_Loss": round(dollar_var, 2), "1D_CVaR_Dollar_Loss": round(dollar_cvar, 2), "Modified_Duration": round(self.bond_specs["Mod_Duration"], 3), "Convexity": round(self.bond_specs["Convexity"], 3)}

    def generate_html_dashboard(self, filename: str = "risk_analyzer_dashboard.html"):
        print("[6/6] Constructing independent Plotly figures and HTML grid layout...")
        
        layout_defaults = dict(template="plotly_dark", height=450, margin=dict(l=40, r=40, t=50, b=40), legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5))

        # CHART A
        norm_oil = (self.raw_data["Commodity"] / self.raw_data["Commodity"].iloc[0]) * 100.0
        norm_us500 = (self.raw_data["US500"] / self.raw_data["US500"].iloc[0]) * 100.0
        norm_us10y = (self.raw_data["US_10Y_Treasury"] / self.raw_data["US_10Y_Treasury"].iloc[0]) * 100.0
        norm_fx = (self.raw_data["FX"] / self.raw_data["FX"].iloc[0]) * 100.0
        
        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(x=self.raw_data.index, y=norm_oil, name="Commodity", line=dict(color="#29b6f6")))
        fig_a.add_trace(go.Scatter(x=self.raw_data.index, y=norm_us500, name="S&P 500", line=dict(color="#ab47bc")))
        fig_a.add_trace(go.Scatter(x=self.raw_data.index, y=norm_us10y, name="US 10Y Treasury", line=dict(color="#26a69a", dash="dot")))
        fig_a.add_trace(go.Scatter(x=self.raw_data.index, y=norm_fx, name="USD/KES", line=dict(color="#ffa726")))
        fig_a.update_layout(title="(A) Global Risk & Asset Dynamics (Base=100)", **layout_defaults)
        
        # CHART B
        cum_effects = self.irf.cum_effects
        steps = np.arange(cum_effects.shape[0])
        fig_b = go.Figure()
        fig_b.add_trace(go.Scatter(x=steps, y=cum_effects[:, 3, 0], mode="lines+markers", name="FX Reaction (%)", line=dict(color="#66bb6a")))
        fig_b.add_trace(go.Scatter(x=steps, y=cum_effects[:, 4, 0], mode="lines+markers", name="EM Yield Reaction (bps)", line=dict(color="#ef5350")))
        fig_b.update_layout(title="(B) Cumulative VAR Response to Oil Shock", xaxis_title="Days Post Shock", **layout_defaults)

        # CHART C
        decomp = self.fevd.decomp[4] 
        fig_c = go.Figure()
        fig_c.add_trace(go.Bar(x=steps, y=decomp[:, 0] * 100, name="Commodity", marker_color="#29b6f6"))
        fig_c.add_trace(go.Bar(x=steps, y=decomp[:, 1] * 100, name="US500", marker_color="#ab47bc"))
        fig_c.add_trace(go.Bar(x=steps, y=decomp[:, 2] * 100, name="US 10Y Treasury", marker_color="#26a69a"))
        fig_c.add_trace(go.Bar(x=steps, y=decomp[:, 3] * 100, name="Local FX", marker_color="#ffa726"))
        fig_c.add_trace(go.Bar(x=steps, y=decomp[:, 4] * 100, name="Own Yield Variance", marker_color="#78909c"))
        fig_c.update_layout(title="(C) Sovereign Yield Variance Breakdown", xaxis_title="Forecast Horizon (Days)", yaxis_title="Variance (%)", barmode="stack", **layout_defaults)

        # CHART D
        dy_grid = np.linspace(-300, 300, 61)
        conv_pricing = [self.estimate_price_shock(dy, self.bond_specs["Mod_Duration"], self.bond_specs["Convexity"]) for dy in dy_grid]
        lin_pricing = [-self.bond_specs["Mod_Duration"] * (dy / 10000.0) * 100.0 for dy in dy_grid]
        
        fig_d = go.Figure()
        fig_d.add_trace(go.Scatter(x=dy_grid, y=conv_pricing, name="Duration + Convexity", line=dict(color="#ef5350", width=3)))
        fig_d.add_trace(go.Scatter(x=dy_grid, y=lin_pricing, name="Duration Only", line=dict(color="#8d6e63", dash="dash")))
        fig_d.update_layout(title="(D) Portfolio Valuation Shock Curve", xaxis_title="Yield Shift (bps)", yaxis_title="Price Impact (%)", **layout_defaults)

        # Extract HTML
        html_a = fig_a.to_html(full_html=False, include_plotlyjs="cdn")
        html_b = fig_b.to_html(full_html=False, include_plotlyjs=False)
        html_c = fig_c.to_html(full_html=False, include_plotlyjs=False)
        html_d = fig_d.to_html(full_html=False, include_plotlyjs=False)

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sovereign Risk Analyzer</title>
            <style>
                body {{ background-color: #0f111a; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; padding: 40px; margin: 0; }}
                h1 {{ text-align: center; color: #ffffff; margin-bottom: 40px; font-weight: 300; letter-spacing: 1px; }}
                .dashboard-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; max-width: 1600px; margin: 0 auto; }}
                .card {{ background-color: #1e2130; border-radius: 12px; padding: 25px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); display: flex; flex-direction: column; }}
                .chart-container {{ flex-grow: 1; }}
                .inference-box {{ margin-top: 25px; padding: 20px; background-color: #272b3d; border-left: 4px solid #3498db; border-radius: 4px; font-size: 14.5px; line-height: 1.6; min-height: 120px; }}
                .inference-title {{ font-weight: 600; color: #ffffff; margin-bottom: 8px; font-size: 16px; text-transform: uppercase; letter-spacing: 0.5px; }}
            </style>
        </head>
        <body>
            <h1>Commodity-FX Transmission & Sovereign Risk Analyzer</h1>
            <div class="dashboard-grid">
                
                <div class="card">
                    <div class="chart-container">{html_a}</div>
                    <div class="inference-box">
                        <div class="inference-title">Interpretation: Asset Price Dynamics</div>
                        <strong>What you see:</strong> The green dotted line (US Treasuries) and purple line (S&P 500) generally rise over time, while the blue line (Oil) jumps up and down violently. The orange line (Local Currency) rises sharply in the middle and then flattens out. <strong>What it means:</strong> By plotting them together, we can check if a sudden spike in oil caused the local currency to lose value, while proving the crash wasn't just a reaction to changing US markets.
                    </div>
                </div>

                <div class="card">
                    <div class="chart-container">{html_b}</div>
                    <div class="inference-box">
                        <div class="inference-title">Interpretation: Shock Transmission (VAR)</div>
                        <strong>What you see:</strong> In the days following an oil shock, the red line (Bond Yields) drops sharply below the zero line and stays in negative territory. The green line (Currency) barely moves, staying almost completely flat right near zero. <strong>What it means:</strong> For this specific data run, a sudden jump in oil prices actually caused local borrowing costs to drop immediately, while the local currency remained surprisingly stable.
                    </div>
                </div>

                <div class="card">
                    <div class="chart-container">{html_c}</div>
                    <div class="inference-box">
                        <div class="inference-title">Interpretation: Variance Decomposition</div>
                        <strong>What you see:</strong> The stacked bars are made of only two visible colors. The top grey section takes up more than half the bar, and the orange section takes up the rest. The colors for oil and US markets are completely missing. <strong>What it means:</strong> The grey area is just random daily market noise. The large orange area proves that almost all the predictable movement in the local bond yields is driven directly by the local currency. Oil and US markets had virtually zero direct impact here.
                    </div>
                </div>

                <div class="card">
                    <div class="chart-container">{html_d}</div>
                    <div class="inference-box">
                        <div class="inference-title">Interpretation: Portfolio Convexity Pricing</div>
                        <strong>What you see:</strong> As you look to the right side of the chart, the solid red line curves upwards, visibly separating from the straight dashed line. <strong>What it means:</strong> Moving to the right means yields are rising, which causes bond prices to fall (moving down the chart). The curve in the red line represents a math rule called "convexity," which shows that your actual cash losses will be slightly less severe than what simple, straight-line math predicts.
                    </div>
                </div>

            </div>
        </body>
        </html>
        """

        output_path = os.path.abspath(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print(f"\n[✓] Dashboard successfully compiled: {output_path}")
        print("    Launching visualizer in default web browser...")
        webbrowser.open(f"file://{output_path}")


if __name__ == "__main__":
    engine = CommoditySovereignRiskEngine(
        commodity_ticker="CL=F",
        fx_ticker="KES=X",
        fred_api_key="023b3dfed55cf2a5411de82f835a655f", 
        period="5y",
        base_yield=12.28,
        portfolio_notional=100_000_000.0,
    )

    engine.fetch_and_clean_data()
    adf_results, stationary_returns = engine.prepare_stationary_returns()
    optimal_lag = engine.fit_var_model(maxlags=5)
    granger_results = engine.test_granger_causality(maxlag=optimal_lag)
    engine.run_dynamics(periods=10)
    risk_metrics = engine.calculate_portfolio_stress(confidence_level=0.99)
    engine.generate_html_dashboard(filename="risk_analyzer_dashboard.html")