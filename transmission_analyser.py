"""
Commodity-FX Transmission & Bond Risk Analyzer

This project models how global oil price shocks ripple through emerging markets. 
Specifically, it tracks how a spike in Brent Crude drains foreign exchange, 
depreciates the local currency, and ultimately forces domestic sovereign bond 
yields higher, causing capital losses for asset managers.

It handles the entire pipeline: fetching the data, verifying the statistical 
safety of the time-series, mapping the causal chain using a VAR model, and 
finally translating those macroeconomic shocks into hard dollar losses for a 
stylized multi-tenor bond portfolio. 
"""

import os
import time
import logging
import webbrowser
import warnings
import pandas as pd
import numpy as np
import yfinance as yf
import scipy.stats as stats
from statsmodels.tsa.stattools import adfuller, kpss, grangercausalitytests
from statsmodels.tsa.api import VAR
from statsmodels.stats.stattools import durbin_watson
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Suppressing statistical library warnings for a cleaner terminal output
warnings.filterwarnings("ignore")


# -----------------------------------------------------------------------------
# System Logger Configuration
# Sets up a clean, time-stamped logging stream for the terminal.
# -----------------------------------------------------------------------------
class SystemConfig:
    @staticmethod
    def setup_logger():
        logger = logging.getLogger("MacroQuantEngine")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

log = SystemConfig.setup_logger()


# -----------------------------------------------------------------------------
# Data Ingestion & Alignment
# Pulls the raw financial data from Yahoo Finance and aligns the international 
# trading calendars so that every asset has matching dates and no missing gaps.
# -----------------------------------------------------------------------------
class DataIngestion:
    def __init__(self, start_date: str = "2015-01-01"):
        self.start_date = start_date
        self.tickers = {
            'Brent_Oil': 'BZ=F',
            'USD_KES': 'USDKES=X',
            'Sovereign_Proxy': 'EMB' 
        }
        self.raw_data = None
        self.monthly_data = None

    def fetch_market_data(self) -> pd.DataFrame:
        log.info("Fetching market data series...")
        data_frames = {}
        for asset_name, ticker in self.tickers.items():
            log.info(f"Downloading stream: {asset_name} ({ticker})")
            df = yf.download(ticker, start=self.start_date, progress=False)['Close']
            if isinstance(df, pd.DataFrame):
                data_frames[asset_name] = df.squeeze()
            else:
                data_frames[asset_name] = df

        self.raw_data = pd.DataFrame(data_frames)
        self.raw_data.index = pd.to_datetime(self.raw_data.index).tz_localize(None)
        return self.raw_data

    def clean_and_resample(self) -> pd.DataFrame:
        log.info("Synchronizing global holiday calendars & resampling to Month-End.")
        daily_clean = self.raw_data.ffill(limit=3).dropna()
        self.monthly_data = daily_clean.resample('ME').last().dropna()
        return self.monthly_data

    def run_descriptive_stats(self):
        log.info("Running descriptive statistics to check for normal distributions.")
        print("\n" + "=" * 85)
        print("          DESCRIPTIVE STATISTICS & DISTRIBUTION ALIGNMENT          ")
        print("=" * 85)
        
        for col in self.monthly_data.columns:
            series = self.monthly_data[col].pct_change().dropna()
            skew = stats.skew(series)
            kurtosis = stats.kurtosis(series)
            _, p_val = stats.jarque_bera(series)
            
            is_normal = "Yes" if p_val > 0.05 else "No (Fat Tails)"
            print(f"Asset: {col:<15} | Skew: {skew:>6.2f} | Kurtosis: {kurtosis:>6.2f} | Normal? {is_normal}")
        print("=" * 85 + "\n")


# -----------------------------------------------------------------------------
# Stationarity & Returns Engine
# Time-series models break if the data is trending unpredictably. This section 
# converts price levels into stable returns and runs strict tests (ADF and KPSS) 
# to mathematically prove the data is safe to model.
# -----------------------------------------------------------------------------
class StationarityEngine:
    def __init__(self, monthly_data: pd.DataFrame):
        self.raw_data = monthly_data.copy()
        self.stationary_data = None
        
    def transform_data(self) -> pd.DataFrame:
        log.info("Transforming price levels to continuous stationary distributions.")
        df = pd.DataFrame(index=self.raw_data.index)
        
        df['Brent_Ret'] = np.log(self.raw_data['Brent_Oil'] / self.raw_data['Brent_Oil'].shift(1))
        df['USDKES_Ret'] = np.log(self.raw_data['USD_KES'] / self.raw_data['USD_KES'].shift(1))
        df['Sov_Proxy_Diff'] = self.raw_data['Sovereign_Proxy'] - self.raw_data['Sovereign_Proxy'].shift(1)
        
        self.stationary_data = df.dropna()
        return self.stationary_data

    def run_dual_stationarity_tests(self):
        log.info("Running dual-stationarity checks (ADF + KPSS).")
        print("\n" + "=" * 85)
        print("          DUAL-STATIONARITY DIAGNOSTICS (ADF & KPSS)        ")
        print("=" * 85)
        for col in self.stationary_data.columns:
            series = self.stationary_data[col]
            
            adf_result = adfuller(series, autolag='AIC')
            adf_p = adf_result[1]
            adf_pass = "PASS" if adf_p < 0.05 else "FAIL"
            
            kpss_result = kpss(series, regression='c', nlags='auto')
            kpss_p = kpss_result[1]
            kpss_pass = "PASS" if kpss_p > 0.05 else "FAIL"
            
            overall = "STATIONARY (I(0))" if (adf_pass == "PASS" and kpss_pass == "PASS") else "REQUIRES DIFFERENCING"
            
            print(f"Variable: {col:<15} | ADF p: {adf_p:.4f} ({adf_pass}) | KPSS p: {kpss_p:.4f} ({kpss_pass}) | {overall}")
        print("=" * 85 + "\n")


# -----------------------------------------------------------------------------
# Causal Modeling & Vector Autoregression (VAR)
# This is the core engine. It checks if oil statistically causes currency moves 
# (Granger Causality), and then fits a VAR model to quantify exactly how shocks 
# ripple from one asset to another over time.
# -----------------------------------------------------------------------------
class VAREngine:
    def __init__(self, stationary_data: pd.DataFrame):
        self.ordered_data = stationary_data[['Brent_Ret', 'USDKES_Ret', 'Sov_Proxy_Diff']]
        self.model = None
        self.results = None

    def run_granger_causality(self):
        log.info("Computing Granger Causality Matrix...")
        print("\n" + "=" * 85)
        print("          GRANGER CAUSALITY MATRIX (Max Lag=3)          ")
        print("=" * 85)
        
        test_data_1 = self.ordered_data[['USDKES_Ret', 'Brent_Ret']]
        res_1 = grangercausalitytests(test_data_1, maxlag=[3], verbose=False)
        p_val_1 = res_1[3][0]['ssr_ftest'][1]
        
        test_data_2 = self.ordered_data[['Sov_Proxy_Diff', 'USDKES_Ret']]
        res_2 = grangercausalitytests(test_data_2, maxlag=[3], verbose=False)
        p_val_2 = res_2[3][0]['ssr_ftest'][1]
        
        print(f"H0: Brent Crude DOES NOT cause USD/KES Depreciation : P-Value = {p_val_1:.4f}")
        print(f"H0: USD/KES Depreciation DOES NOT cause Yield Spike : P-Value = {p_val_2:.4f}")
        print("-> A p-value < 0.05 rejects H0, proving statistical causality.")
        print("=" * 85 + "\n")

    def fit_model(self, max_lags: int = 6):
        log.info(f"Initializing VAR Engine. Scanning for optimal lag structure.")
        self.model = VAR(self.ordered_data)
        self.results = self.model.fit(maxlags=max_lags, ic='aic')
        
        print("\n" + "=" * 85)
        print("          CHOLESKY-ORDERED VAR MODEL FITTING          ")
        print("=" * 85)
        print(f"Optimal Lags Selected : {self.results.k_ar} months")
        print(f"System AIC Score      : {self.results.aic:.4f}")
        print("-" * 85)
        
        dw_stats = durbin_watson(self.results.resid)
        print("Residual Autocorrelation Diagnostics (Durbin-Watson Target ~ 2.0):")
        for idx, col in enumerate(self.ordered_data.columns):
            print(f"  -> {col:<15}: {dw_stats[idx]:.2f}")
            
        print("-" * 85)
        print("Causal Hierarchy Imposed (Structural Identification):")
        print(" 1. Brent_Ret      [Global Exogenous Supply Shock]")
        print(" 2. USDKES_Ret     [Terms of Trade / FX Drain]")
        print(" 3. Sov_Proxy_Diff [Domestic Debt Vulnerability]")
        print("=" * 85 + "\n")
        
        return self.results


# -----------------------------------------------------------------------------
# Transmission Dynamics & Variance Decomposition
# Takes the fitted model and simulates a real-world shock (+1 standard deviation 
# jump in oil prices), charting its month-by-month impact over the next year.
# -----------------------------------------------------------------------------
class TransmissionDynamicsEngine:
    def __init__(self, var_results):
        self.results = var_results
        self.horizon = 12
        self.irf = None
        self.fevd = None
        self.fx_cumulative = None
        self.proxy_cumulative = None
        self.irf_stderr = None

    def simulate_shocks(self):
        log.info("Simulating +1σ Brent Crude Shock over 12-month horizon.")
        self.irf = self.results.irf(self.horizon)
        
        fx_response = self.irf.orth_irfs[:, 1, 0]
        proxy_response = self.irf.orth_irfs[:, 2, 0]
        self.irf_stderr = self.irf.stderr()
        
        self.fx_cumulative = np.cumsum(fx_response)
        self.proxy_cumulative = np.cumsum(proxy_response)
        
        max_fx_impact = self.fx_cumulative[-1]
        half_life_threshold = max_fx_impact * 0.5
        half_life_month = int(np.argmax(np.abs(self.fx_cumulative) >= np.abs(half_life_threshold))) + 1

        print("\n" + "=" * 85)
        print("          SHOCK TRANSMISSION PROFILING       ")
        print("=" * 85)
        print(f"Terminal FX Depreciation (Month 12)        : {max_fx_impact * 100:.2f}%")
        print(f"Terminal Sovereign Spread Impact (Month 12): {self.proxy_cumulative[-1]:.2f} pts")
        print(f"Shock Pass-Through Half-Life               : {half_life_month} Months")
        print("=" * 85 + "\n")
        
    def variance_decomposition(self):
        log.info("Running Forecast Error Variance Decomposition (FEVD).")
        self.fevd = self.results.fevd(self.horizon)


# -----------------------------------------------------------------------------
# Portfolio Stress Tester
# Bridges the gap between statistics and finance. Maps the simulated yield 
# curve shifts into a fixed-income portfolio to calculate actual capital loss 
# using Modified Duration and Convexity formulas.
# -----------------------------------------------------------------------------
class FixedIncomeStressTester:
    def __init__(self, simulated_proxy_path, portfolio_size=50000000):
        self.portfolio_size = portfolio_size
        self.yield_trajectory_decimal = (np.abs(simulated_proxy_path) * 100) / 10000.0
        
        # Stylized asset-liability weights and bond metrics
        self.portfolios = {
            '2-Year Sovereign': {'D_mod': 1.85, 'Convexity': 4.5, 'Weight': 0.20},
            '5-Year Sovereign': {'D_mod': 3.65, 'Convexity': 18.2, 'Weight': 0.35},
            '10-Year Sovereign': {'D_mod': 5.80, 'Convexity': 48.6, 'Weight': 0.30},
            '30-Year Sovereign': {'D_mod': 11.20, 'Convexity': 185.4, 'Weight': 0.15}
        }
        self.monthly_drawdowns = {}
        self.aggregate_loss_path = np.zeros(len(self.yield_trajectory_decimal))

    def run_stress_test(self):
        log.info(f"Executing non-linear duration/convexity shock on ${self.portfolio_size/1e6:.1f}M book.")
        print("\n" + "=" * 85)
        print("          INSTITUTIONAL PORTFOLIO STRESS-TEST      ")
        print("=" * 85)
        peak_yield_bps = np.max(self.yield_trajectory_decimal) * 10000
        print(f"Peak Assumed Yield Curve Shift : +{peak_yield_bps:.0f} bps")
        print("-" * 85)
        
        for name, metrics in self.portfolios.items():
            d_mod, c, w = metrics['D_mod'], metrics['Convexity'], metrics['Weight']
            sub_portfolio = self.portfolio_size * w
            
            # Non-linear pricing formula
            linear_effect = -d_mod * self.yield_trajectory_decimal
            convexity_cushion = 0.5 * c * (self.yield_trajectory_decimal ** 2)
            net_drawdown_pct = linear_effect + convexity_cushion
            dollar_losses = net_drawdown_pct * sub_portfolio
            
            self.monthly_drawdowns[name] = {
                'pct_drawdown': net_drawdown_pct,
                'dollar_losses': dollar_losses
            }
            self.aggregate_loss_path += dollar_losses
            
            print(f"[{name}] (Allocation: {w*100:.0f}%)")
            print(f"  Net Terminal Capital Loss : {net_drawdown_pct[-1] * 100:8.2f}%  ->  ${dollar_losses[-1]:,.2f}")
            print()
            
        print("-" * 85)
        print(f"AGGREGATE FUND LOSS AT HORIZON END: ${self.aggregate_loss_path[-1]:,.2f}")
        print("=" * 85 + "\n")


# -----------------------------------------------------------------------------
# Plotly Visualization Engine
# Generates the final output: interactive HTML dashboards (2D charts, Heatmaps, 
# and 3D Volatility Surfaces) and launches them locally in the browser.
# -----------------------------------------------------------------------------
class VisualizerDashboard:
    def __init__(self, stationary_data, dynamics, stress_tester):
        self.data = stationary_data
        self.dynamics = dynamics
        self.stress = stress_tester
        self.generated_files = []

    def open_in_browser(self, filename):
        file_path = f"file://{os.path.realpath(filename)}"
        webbrowser.open(file_path, new=2)

    def generate_macro_dashboard(self, filename="1_macro_transmission.html"):
        log.info("Generating Macro Transmission Dashboard...")
        months = list(range(1, len(self.dynamics.fx_cumulative) + 1))
        
        fig = make_subplots(
            rows=2, cols=2, 
            subplot_titles=("Cumulative FX Depreciation", 
                            "Sovereign Spread Impact", 
                            "FEVD: % Variance Explained by Oil", 
                            "12-Month Rolling Beta (Elasticity)"),
            vertical_spacing=0.15,
            horizontal_spacing=0.10
        )

        fig.add_trace(go.Scatter(x=months, y=self.dynamics.fx_cumulative * 100,
                                 mode='lines+markers', line=dict(color='#ef553b', width=3),
                                 name='USD/KES Impact (%)'), row=1, col=1)

        fig.add_trace(go.Scatter(x=months, y=self.dynamics.proxy_cumulative,
                                 mode='lines+markers', line=dict(color='#ffa15a', width=3),
                                 name='Spread Impact (pts)'), row=1, col=2)

        fevd_matrix = self.dynamics.fevd.decomp[:, :, 0] * 100 
        fig.add_trace(go.Heatmap(z=fevd_matrix, x=[f"M{m}" for m in months],
                                 y=['Brent', 'USD/KES', 'Sov Spread'],
                                 colorscale='Viridis', name='FEVD',
                                 colorbar=dict(len=0.45, y=0.22, x=0.46, thickness=15)), row=2, col=1)

        rolling_beta = (self.data['USDKES_Ret'].rolling(12).cov(self.data['Brent_Ret']) / 
                        self.data['Brent_Ret'].rolling(12).var()).dropna()
        fig.add_trace(go.Scatter(x=rolling_beta.index, y=rolling_beta,
                                 mode='lines', fill='tozeroy', line=dict(color='#00cc96'),
                                 name='Rolling Beta'), row=2, col=2)

        fig.update_layout(
            template='plotly_dark', height=850, 
            title='<b>Macroeconomic Shock Transmission Suite</b>',
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            margin=dict(t=80, b=80, l=40, r=40)
        )
        fig.write_html(filename, include_plotlyjs='cdn')
        self.generated_files.append(filename)

    def generate_3d_yield_curve_surface(self, filename="2_yield_curve_surface.html"):
        log.info("Generating 3D Yield Curve Volatility Surface...")
        
        tenors = [2, 5, 10, 30]
        months = list(range(1, 13))
        z_data = []
        base_shock = self.stress.yield_trajectory_decimal * 10000
        
        for tenor in tenors:
            tenor_multiplier = 1.0 if tenor <= 5 else (0.8 if tenor == 10 else 0.5)
            z_data.append(base_shock * tenor_multiplier)
            
        fig = go.Figure(data=[go.Surface(z=z_data, x=months, y=[f"{t}Y" for t in tenors],
                                         colorscale='Plasma')])
        
        fig.update_layout(
            template='plotly_dark', height=800,
            title='<b>3D Yield Curve Shock Surface</b><br><sup>Time Horizon vs Bond Tenor vs Spread Shock (bps)</sup>',
            scene=dict(
                xaxis_title='Months Post-Shock',
                yaxis_title='Bond Tenor',
                zaxis_title='Yield Shock (bps)',
                aspectratio=dict(x=2, y=1, z=0.8) 
            ),
            margin=dict(t=80, b=40, l=0, r=0)
        )
        fig.write_html(filename, include_plotlyjs='cdn')
        self.generated_files.append(filename)

    def generate_portfolio_stress_dashboard(self, filename="3_portfolio_stress.html"):
        log.info("Generating Portfolio Drawdown Dashboard...")
        fig = go.Figure()
        months = [f"M{m}" for m in range(1, 13)]
        
        fig.add_trace(go.Scatter(
            x=months, y=self.stress.aggregate_loss_path,
            name="Aggregate Fund Drawdown",
            fill='tozeroy', mode='none', fillcolor='rgba(239, 85, 59, 0.15)'
        ))

        colors = ['#636efa', '#ab63fa', '#00cc96', '#ffa15a']
        for (name, data), color in zip(self.stress.monthly_drawdowns.items(), colors):
            fig.add_trace(go.Scatter(x=months, y=data['dollar_losses'],
                                     mode='lines+markers', name=name,
                                     line=dict(color=color, width=3)))

        fig.update_layout(
            template='plotly_dark', height=750, hovermode='x unified',
            title='<b>Dynamic Fund Drawdowns ($50M AUM)</b><br><sup>Factoring Non-Linear Convexity across Yield Curve</sup>',
            yaxis=dict(title='Capital Impact (USD)', tickprefix='$', tickformat=','),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            margin=dict(t=80, b=80, l=60, r=40)
        )
        
        fig.write_html(filename, include_plotlyjs='cdn')
        self.generated_files.append(filename)

    def launch_all(self):
        log.info("Deploying generated HTML files to browser...")
        for file in self.generated_files:
            self.open_in_browser(file)
            time.sleep(1.5)


# -----------------------------------------------------------------------------
# Main Pipeline Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    log.info("--- INITIATING COMMODITY-FX TRANSMISSION PIPELINE ---")
    
    ingestion = DataIngestion(start_date="2015-01-01")
    ingestion.fetch_market_data()
    monthly_df = ingestion.clean_and_resample()
    ingestion.run_descriptive_stats()
    
    stationarity = StationarityEngine(monthly_df)
    stationary_df = stationarity.transform_data()
    stationarity.run_dual_stationarity_tests()
    
    var_engine = VAREngine(stationary_df)
    var_engine.run_granger_causality()
    var_results = var_engine.fit_model(max_lags=6)
    
    dynamics = TransmissionDynamicsEngine(var_results)
    dynamics.simulate_shocks()
    dynamics.variance_decomposition()
    
    stress_tester = FixedIncomeStressTester(dynamics.proxy_cumulative, portfolio_size=50000000)
    stress_tester.run_stress_test()
    
    visualizer = VisualizerDashboard(stationary_df, dynamics, stress_tester)
    visualizer.generate_macro_dashboard()
    visualizer.generate_3d_yield_curve_surface()
    visualizer.generate_portfolio_stress_dashboard()
    
    print("\n" + "=" * 85)
    print(" [✓] PIPELINE EXECUTION COMPLETE.")
    print("=" * 85 + "\n")
    
    visualizer.launch_all()
