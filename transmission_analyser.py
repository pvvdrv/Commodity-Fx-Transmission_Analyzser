"""
Commodity-FX Transmission & Bond Risk Analyzer (Dynamic ARX & GARCH Edition)

This pipeline tracks how a global oil price shock drains foreign exchange, 
depreciates the local currency, and forces domestic sovereign bond yields higher.
It replaces complex SVAR mechanics with intuitive Two-Stage Distributed Lag 
regressions and integrates GARCH(1,1) to model commodity volatility clustering.
"""

import os
import time
import logging
import webbrowser
import warnings
import pandas as pd
import numpy as np
import yfinance as yf
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from arch import arch_model
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")


# -----------------------------------------------------------------------------
# System Logger Configuration
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


# -----------------------------------------------------------------------------
# Stationarity & Returns Engine (Simplified to just ADF)
# -----------------------------------------------------------------------------
class StationarityEngine:
    def __init__(self, monthly_data: pd.DataFrame):
        self.raw_data = monthly_data.copy()
        self.stationary_data = None
        
    def transform_data(self) -> pd.DataFrame:
        log.info("Transforming price levels to continuous log returns.")
        df = pd.DataFrame(index=self.raw_data.index)
        
        df['Brent_Ret'] = np.log(self.raw_data['Brent_Oil'] / self.raw_data['Brent_Oil'].shift(1))
        df['USDKES_Ret'] = np.log(self.raw_data['USD_KES'] / self.raw_data['USD_KES'].shift(1))
        df['Sov_Proxy_Diff'] = self.raw_data['Sovereign_Proxy'] - self.raw_data['Sovereign_Proxy'].shift(1)
        
        self.stationary_data = df.dropna()
        return self.stationary_data

    def run_adf_tests(self):
        log.info("Running Augmented Dickey-Fuller (ADF) stationarity checks.")
        print("\n" + "=" * 85)
        print("          STATIONARITY DIAGNOSTICS (ADF)        ")
        print("=" * 85)
        for col in self.stationary_data.columns:
            series = self.stationary_data[col]
            adf_p = adfuller(series, autolag='AIC')[1]
            status = "PASS (Stationary)" if adf_p < 0.05 else "FAIL (Unit Root)"
            print(f"Variable: {col:<15} | ADF p-value: {adf_p:.4f} | {status}")
        print("=" * 85 + "\n")


# -----------------------------------------------------------------------------
# Risk Engine: GARCH(1,1) Volatility Modeling
# -----------------------------------------------------------------------------
class GARCHEngine:
    def __init__(self, stationary_data: pd.DataFrame):
        self.brent_returns = stationary_data['Brent_Ret'] * 100  # Scaled for optimizer
        self.garch_volatility = None

    def fit_garch(self):
        log.info("Fitting GARCH(1,1) to model Brent Crude volatility clustering.")
        # p=1 (lagged variance), q=1 (lagged squared shock)
        model = arch_model(self.brent_returns, vol='Garch', p=1, q=1, rescale=False)
        results = model.fit(disp='off')
        
        self.garch_volatility = results.conditional_volatility / 100  # Scale back
        
        print("\n" + "=" * 85)
        print("          GARCH(1,1) VOLATILITY ESTIMATION (BRENT CRUDE)        ")
        print("=" * 85)
        print(f"Omega (Baseline Variance): {results.params['omega']:.6f}")
        print(f"Alpha (Shock Sensitivity): {results.params['alpha[1]']:.4f}")
        print(f"Beta (Volatility Persistence): {results.params['beta[1]']:.4f}")
        print("-> A high Beta means once oil gets volatile, it stays volatile for months.")
        print("=" * 85 + "\n")


# -----------------------------------------------------------------------------
# Transmission Engine: Two-Stage ARX Regression
# -----------------------------------------------------------------------------
class TransmissionRegressionEngine:
    def __init__(self, stationary_data: pd.DataFrame):
        self.df = stationary_data
        self.stage1_model = None
        self.stage2_model = None

    def run_lead_lag_analysis(self):
        log.info("Running Lead-Lag Cross Correlation...")
        print("\n" + "=" * 85)
        print("          LEAD-LAG CORRELATION (THE 'FOOTPRINTS' TEST)        ")
        print("=" * 85)
        
        for lag in range(4):
            corr = self.df['Brent_Ret'].shift(lag).corr(self.df['USDKES_Ret'])
            print(f"Correlation: Brent (Lag {lag}) -> USD/KES (Today) : {corr:.4f}")
        print("-> Peak correlation at Lag > 0 proves oil leads the currency.")
        print("=" * 85 + "\n")

    def fit_two_stage_models(self):
        log.info("Fitting Two-Stage Autoregressive Distributed Lag (ARX) models.")
        
        # Prep Data with Lags
        df_model = self.df.copy()
        df_model['USDKES_Lag1'] = df_model['USDKES_Ret'].shift(1)
        df_model['Sov_Proxy_Lag1'] = df_model['Sov_Proxy_Diff'].shift(1)
        df_model = df_model.dropna()

        # Stage 1: How Brent hits USD/KES (accounting for currency momentum)
        X1 = sm.add_constant(df_model[['Brent_Ret', 'USDKES_Lag1']])
        y1 = df_model['USDKES_Ret']
        self.stage1_model = sm.OLS(y1, X1).fit()

        # Stage 2: How USD/KES depreciation hits Sovereign Spreads
        X2 = sm.add_constant(df_model[['USDKES_Ret', 'Sov_Proxy_Lag1']])
        y2 = df_model['Sov_Proxy_Diff']
        self.stage2_model = sm.OLS(y2, X2).fit()
        
        print("\n" + "=" * 85)
        print("          TWO-STAGE MACRO TRANSMISSION REGRESSION (ARX)        ")
        print("=" * 85)
        print(f"Stage 1 (FX Impact) R-Squared : {self.stage1_model.rsquared:.4f}")
        print(f"Stage 2 (Yield Impact) R-Squared : {self.stage2_model.rsquared:.4f}")
        print("=" * 85 + "\n")

    def simulate_scenario(self, shock_magnitude=0.20, horizon=12):
        log.info(f"Simulating a {shock_magnitude*100}% Brent Crude Shock over {horizon} months.")
        
        fx_path = np.zeros(horizon)
        yield_path = np.zeros(horizon)
        
        # Month 0: Initial Shock
        fx_path[0] = self.stage1_model.params['Brent_Ret'] * shock_magnitude
        yield_path[0] = self.stage2_model.params['USDKES_Ret'] * fx_path[0]
        
        # Month 1 to Horizon (Autoregressive Ripple Effect)
        for t in range(1, horizon):
            fx_path[t] = self.stage1_model.params['USDKES_Lag1'] * fx_path[t-1]
            yield_path[t] = self.stage2_model.params['Sov_Proxy_Lag1'] * yield_path[t-1] + \
                            self.stage2_model.params['USDKES_Ret'] * fx_path[t]
            
        fx_cumulative = np.cumsum(fx_path)
        yield_cumulative = np.cumsum(yield_path)
        
        return fx_cumulative, yield_cumulative


# -----------------------------------------------------------------------------
# Portfolio Stress Tester
# -----------------------------------------------------------------------------
class FixedIncomeStressTester:
    def __init__(self, simulated_yield_path, portfolio_size=50000000):
        self.portfolio_size = portfolio_size
        self.yield_trajectory_decimal = (np.abs(simulated_yield_path) * 100) / 10000.0
        
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
        for name, metrics in self.portfolios.items():
            d_mod, c, w = metrics['D_mod'], metrics['Convexity'], metrics['Weight']
            sub_portfolio = self.portfolio_size * w
            
            linear_effect = -d_mod * self.yield_trajectory_decimal
            convexity_cushion = 0.5 * c * (self.yield_trajectory_decimal ** 2)
            net_drawdown_pct = linear_effect + convexity_cushion
            dollar_losses = net_drawdown_pct * sub_portfolio
            
            self.monthly_drawdowns[name] = {
                'pct_drawdown': net_drawdown_pct,
                'dollar_losses': dollar_losses
            }
            self.aggregate_loss_path += dollar_losses


# -----------------------------------------------------------------------------
# Plotly Visualization Engine
# -----------------------------------------------------------------------------
class VisualizerDashboard:
    def __init__(self, stationary_data, garch_vol, fx_path, yield_path, stress_tester):
        self.data = stationary_data
        self.garch_vol = garch_vol
        self.fx_path = fx_path
        self.yield_path = yield_path
        self.stress = stress_tester
        self.generated_files = []

    def open_in_browser(self, filename):
        file_path = f"file://{os.path.realpath(filename)}"
        webbrowser.open(file_path, new=2)

    def generate_macro_dashboard(self, filename="1_macro_transmission.html"):
        log.info("Generating Macro Transmission & GARCH Dashboard...")
        months = list(range(1, len(self.fx_path) + 1))
        
        fig = make_subplots(
            rows=2, cols=2, 
            subplot_titles=("Simulated FX Depreciation Path", 
                            "Simulated Sovereign Yield Impact", 
                            "GARCH(1,1) Oil Volatility Clustering", 
                            "Yield Volatility Proxy"),
            vertical_spacing=0.15,
            horizontal_spacing=0.10
        )

        fig.add_trace(go.Scatter(x=months, y=self.fx_path * 100,
                                 mode='lines+markers', line=dict(color='#ef553b', width=3),
                                 name='USD/KES Impact (%)'), row=1, col=1)

        fig.add_trace(go.Scatter(x=months, y=self.yield_path,
                                 mode='lines+markers', line=dict(color='#ffa15a', width=3),
                                 name='Spread Impact (pts)'), row=1, col=2)

        fig.add_trace(go.Scatter(x=self.garch_vol.index, y=self.garch_vol * 100,
                                 mode='lines', fill='tozeroy', line=dict(color='#ab63fa'),
                                 name='Brent GARCH Vol (%)'), row=2, col=1)

        rolling_yield_vol = self.data['Sov_Proxy_Diff'].rolling(12).std()
        fig.add_trace(go.Scatter(x=rolling_yield_vol.index, y=rolling_yield_vol,
                                 mode='lines', fill='tozeroy', line=dict(color='#00cc96'),
                                 name='Yield Volatility'), row=2, col=2)

        fig.update_layout(
            template='plotly_dark', height=850, 
            title='<b>Macroeconomic Shock & Risk Spillover Suite</b>',
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
            
        fig = go.Figure(data=[go.Surface(
            z=z_data, x=months, y=[f"{t}Y" for t in tenors],
            colorscale='Plasma',
            colorbar=dict(title='Shock (bps)', len=0.6, thickness=20, x=0.9)
        )])
        
        fig.update_layout(
            template='plotly_dark', height=850,
            title=dict(
                text='<b>3D Yield Curve Volatility Surface</b><br><sup>Time Horizon vs Bond Tenor vs Spread Shock (bps)</sup>',
                x=0.5, y=0.92, xanchor='center', yanchor='top'
            ),
            scene=dict(
                xaxis_title='Months Post-Shock', yaxis_title='Bond Tenor', zaxis_title='Yield Shock (bps)',
                aspectratio=dict(x=1.4, y=1.2, z=0.8),
                camera=dict(eye=dict(x=1.6, y=-1.6, z=1.0))
            ),
            margin=dict(t=120, b=50, l=50, r=50)
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
    log.info("--- INITIATING DYNAMIC ARX & GARCH TRANSMISSION PIPELINE ---")
    
    ingestion = DataIngestion(start_date="2015-01-01")
    ingestion.fetch_market_data()
    monthly_df = ingestion.clean_and_resample()
    
    stationarity = StationarityEngine(monthly_df)
    stationary_df = stationarity.transform_data()
    stationarity.run_adf_tests()
    
    garch_engine = GARCHEngine(stationary_df)
    garch_engine.fit_garch()
    
    regression_engine = TransmissionRegressionEngine(stationary_df)
    regression_engine.run_lead_lag_analysis()
    regression_engine.fit_two_stage_models()
    fx_cumulative, yield_cumulative = regression_engine.simulate_scenario(shock_magnitude=0.20, horizon=12)
    
    stress_tester = FixedIncomeStressTester(yield_cumulative, portfolio_size=50000000)
    stress_tester.run_stress_test()
    
    visualizer = VisualizerDashboard(stationary_df, garch_engine.garch_volatility, 
                                     fx_cumulative, yield_cumulative, stress_tester)
    visualizer.generate_macro_dashboard()
    visualizer.generate_3d_yield_curve_surface()
    visualizer.generate_portfolio_stress_dashboard()
    
    print("\n" + "=" * 85)
    print(" [✓] PIPELINE EXECUTION COMPLETE.")
    print("=" * 85 + "\n")
    
    visualizer.launch_all()
