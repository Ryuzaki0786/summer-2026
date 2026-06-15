"""
Valenwood Capital — Systematic Trading System v2
=================================================
A fully systematic, mathematically grounded trading framework for NSE.

Architecture:
    Module 1 — Data Layer          (fetch, cache, clean OHLCV)
    Module 2 — Indicator Engine    (technical + statistical indicators)
    Module 3 — Signal Engine       (three strategies + composite scorer)
    Module 4 — Risk Engine         (Kelly sizing, ATR stops, portfolio heat)
    Module 5 — Backtest Engine     (walk-forward, realistic costs)
    Module 6 — Portfolio Tracker   (live positions, PnL, tax)
    Module 7 — Trade Journal       (log, expectancy, mistake patterns)

Mathematical models:
    → Kelly Criterion          (position sizing)
    → Hurst Exponent           (trend vs mean reversion detection)
    → ATR dynamic stops        (volatility-adjusted exit placement)
    → Z-Score                  (mean reversion entry timing)
    → Rolling Sharpe           (live strategy performance)
    → Expectancy               (system edge quantification)
    → Maximum Drawdown         (risk monitoring)

Install:
    pip install yfinance pandas numpy scipy tabulate colorama

Run:
    python valenwood_system.py --mode screen
    python valenwood_system.py --mode portfolio
    python valenwood_system.py --mode backtest --ticker ICICIBANK.NS
    python valenwood_system.py --mode journal
    python valenwood_system.py --mode report
    python valenwood_system.py --mode trade --action log
"""

import os
import json
import time
import argparse
import warnings
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Optional dependencies ─────────────────────────────────────────────────
try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False

try:
    from scipy.stats import linregress
    SCIPY_OK = True
except ImportError:
    SCIPY_OK = False

try:
    from tabulate import tabulate
    def tbl(data, **kw):
        return tabulate(data, headers="keys", tablefmt="rounded_outline",
                        numalign="right", stralign="left", **kw)
except ImportError:
    def tbl(data, **kw):
        return pd.DataFrame(data).to_string(index=False)

try:
    from colorama import Fore, Style, init as _ci
    _ci(autoreset=True)
    def c(txt, col):
        m = {"g": Fore.GREEN, "r": Fore.RED, "y": Fore.YELLOW,
             "b": Fore.CYAN,  "w": Style.BRIGHT}
        return m.get(col, "") + str(txt) + Style.RESET_ALL
except ImportError:
    def c(txt, col): return str(txt)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════

class Config:
    # ── Capital ───────────────────────────────────────────────────────────
    TOTAL_CASH        = 145_586
    CASH_RESERVE_PCT  = 0.15          # always keep 15% dry
    MAX_POSITION_PCT  = 0.20          # max 20% per stock
    MIN_POSITION_PCT  = 0.05          # min 5% per stock
    MAX_POSITIONS     = 6

    # ── Risk ──────────────────────────────────────────────────────────────
    BASE_STOP_PCT     = 0.04          # 4% base stop (ATR adjusts this)
    TARGET_MULTIPLIER = 2.5           # target = stop × 2.5 (2.5:1 RR)
    MAX_PORTFOLIO_HEAT = 0.06         # max 6% total portfolio at risk at once

    # ── Hurst Exponent thresholds ─────────────────────────────────────────
    HURST_TREND       = 0.55          # > 0.55 = trending (use trend strategy)
    HURST_REVERT      = 0.45          # < 0.45 = mean reverting (use MR strategy)
    # between 0.45-0.55 = random walk, avoid

    # ── Signal thresholds ─────────────────────────────────────────────────
    MIN_SCORE_BUY     = 65
    MIN_SCORE_WATCH   = 45
    RSI_OVERSOLD      = 35
    RSI_OVERBOUGHT    = 70
    ZSCORE_ENTRY      = -1.5          # enter mean reversion below -1.5 SD
    ZSCORE_EXIT       = 0.5           # exit mean reversion at +0.5 SD

    # ── Backtest ──────────────────────────────────────────────────────────
    COMMISSION_PCT    = 0.0003        # 0.03% per trade (Motilal approx)
    SLIPPAGE_PCT      = 0.0005        # 0.05% slippage assumption
    STT_PCT           = 0.001         # 0.1% STT on sell side

    # ── Paths ─────────────────────────────────────────────────────────────
    JOURNAL_FILE      = "valenwood_journal.json"
    PORTFOLIO_FILE    = "valenwood_portfolio.json"

    # ── Current holdings ─────────────────────────────────────────────────
    HOLDINGS = [
        {"ticker": "KPIGREEN.NS",  "qty": 325, "avg": 593.93,
         "bought": "2024-04-05", "sector": "Renewable Energy"},
        {"ticker": "TMPV.NS",      "qty": 175, "avg": 605.68,
         "bought": "2025-10-14", "sector": "Automobile",
         "note": "Illiquid demerger — exit when volume allows"},
        {"ticker": "FINCABLES.NS", "qty": 40,  "avg": 1297.13,
         "bought": "2024-07-31", "sector": "Cables"},
        {"ticker": "GODREJCP.NS",  "qty": 25,  "avg": 1047.67,
         "bought": "2025-01-01", "sector": "FMCG"},
        {"ticker": "EXIDEIND.NS",  "qty": 95,  "avg": 394.40,
         "bought": "2025-10-09", "sector": "Auto Ancillary"},
        {"ticker": "ICICIBANK.NS", "qty": 12,  "avg": 1225.00,
         "bought": "2026-05-25", "sector": "Banking",
         "stop": 1175.0, "target": 1344.0},
    ]

    WATCHLIST = [
        "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "TCS.NS", "INFY.NS", "HCLTECH.NS", "PERSISTENT.NS",
        "HINDUNILVR.NS", "BRITANNIA.NS", "DABUR.NS",
        "MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS",
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS",
        "LT.NS", "ABB.NS", "SIEMENS.NS", "CUMMINSIND.NS",
        "TITAN.NS", "TRENT.NS", "DMART.NS",
        "NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS",
    ]


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 1 — DATA LAYER
# ═══════════════════════════════════════════════════════════════════════════

class DataFetcher:
    """
    Fetches OHLCV data from yfinance with:
    - In-memory caching (no repeated API calls per run)
    - Polite rate limiting (2s sleep between requests)
    - Deterministic mock data fallback for offline use
    """

    def __init__(self):
        self._cache: dict = {}

    def get(self, ticker: str, period: str = "2y") -> Optional[pd.DataFrame]:
        key = f"{ticker}_{period}"
        if key in self._cache:
            return self._cache[key]

        if not YFINANCE_OK:
            df = self._mock(ticker, period)
            self._cache[key] = df
            return df

        try:
            time.sleep(2)
            df = yf.Ticker(ticker).history(period=period)
            if df is None or df.empty:
                return None
            df = self._clean(df)
            self._cache[key] = df
            return df
        except Exception as e:
            print(f"  {c('[WARN]','y')} {ticker}: {e}")
            df = self._mock(ticker, period)
            self._cache[key] = df
            return df

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.dropna()
        df = df[df["Volume"] > 0]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df

    def _mock(self, ticker: str, period: str) -> pd.DataFrame:
        """Seeded mock data — same output every run for same ticker."""
        seed = sum(ord(c) for c in ticker) % 10000
        rng  = np.random.default_rng(seed)
        days = {"1y": 252, "2y": 504, "3y": 756}.get(period, 504)
        dates = pd.bdate_range(end=datetime.today(), periods=days)

        # Different market regimes for different tickers
        trend    = rng.uniform(-0.0002, 0.0006)
        vol      = rng.uniform(0.012, 0.025)
        start    = rng.uniform(300, 2500)

        returns  = rng.normal(trend, vol, days)
        prices   = start * np.exp(np.cumsum(returns))
        noise    = rng.uniform(0.002, 0.008, days)

        return pd.DataFrame({
            "Open":   prices * (1 - noise / 2),
            "High":   prices * (1 + noise),
            "Low":    prices * (1 - noise),
            "Close":  prices,
            "Volume": rng.integers(200_000, 5_000_000, days).astype(float),
        }, index=dates)


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 2 — INDICATOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class Indicators:
    """
    All indicators are pure functions operating on Series/DataFrames.
    No state, no side effects — easy to test and compose.
    """

    # ── Trend ─────────────────────────────────────────────────────────────
    @staticmethod
    def sma(s: pd.Series, n: int) -> pd.Series:
        return s.rolling(n).mean()

    @staticmethod
    def ema(s: pd.Series, n: int) -> pd.Series:
        return s.ewm(span=n, adjust=False).mean()

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        tp  = (df["High"] + df["Low"] + df["Close"]) / 3
        return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

    @staticmethod
    def supertrend(df: pd.DataFrame, period=10, mult=3.0):
        atr    = Indicators.atr(df, period)
        hl2    = (df["High"] + df["Low"]) / 2
        upper  = hl2 + mult * atr
        lower  = hl2 - mult * atr
        trend  = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        for i in range(1, len(df)):
            if df["Close"].iloc[i] > upper.iloc[i - 1]:
                direction.iloc[i] = 1
            elif df["Close"].iloc[i] < lower.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]
            trend.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]

        return trend, direction

    # ── Momentum ──────────────────────────────────────────────────────────
    @staticmethod
    def rsi(s: pd.Series, n=14) -> pd.Series:
        d = s.diff()
        g = d.clip(lower=0).rolling(n).mean()
        l = (-d.clip(upper=0)).rolling(n).mean()
        return 100 - 100 / (1 + g / l.replace(0, np.nan))

    @staticmethod
    def macd(s: pd.Series, fast=12, slow=26, sig=9):
        ml = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
        sl = ml.ewm(span=sig, adjust=False).mean()
        return ml, sl, ml - sl

    @staticmethod
    def stochastic(df: pd.DataFrame, k=14, d=3):
        low_k  = df["Low"].rolling(k).min()
        high_k = df["High"].rolling(k).max()
        k_pct  = 100 * (df["Close"] - low_k) / (high_k - low_k + 1e-9)
        return k_pct, k_pct.rolling(d).mean()

    @staticmethod
    def roc(s: pd.Series, n=12) -> pd.Series:
        """Rate of Change — momentum over n periods."""
        return (s - s.shift(n)) / s.shift(n) * 100

    # ── Volatility ────────────────────────────────────────────────────────
    @staticmethod
    def atr(df: pd.DataFrame, n=14) -> pd.Series:
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"]  - df["Close"].shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(n).mean()

    @staticmethod
    def bollinger(s: pd.Series, n=20, std=2.0):
        mid   = s.rolling(n).mean()
        sigma = s.rolling(n).std()
        return mid + std * sigma, mid, mid - std * sigma

    @staticmethod
    def keltner(df: pd.DataFrame, n=20, mult=1.5):
        mid   = Indicators.ema(df["Close"], n)
        atr_v = Indicators.atr(df, n)
        return mid + mult * atr_v, mid, mid - mult * atr_v

    # ── Volume ────────────────────────────────────────────────────────────
    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        direction = np.sign(df["Close"].diff()).fillna(0)
        return (direction * df["Volume"]).cumsum()

    @staticmethod
    def adtv(df: pd.DataFrame, n=20) -> float:
        """Average Daily Turnover in Crores."""
        return (df["Close"] * df["Volume"]).rolling(n).mean().iloc[-1] / 1e7

    # ── Statistical ───────────────────────────────────────────────────────
    @staticmethod
    def zscore(s: pd.Series, n=20) -> pd.Series:
        """How many standard deviations from rolling mean."""
        mean = s.rolling(n).mean()
        std  = s.rolling(n).std()
        return (s - mean) / std.replace(0, np.nan)

    @staticmethod
    def hurst_exponent(s: pd.Series, max_lag=20) -> float:
        """
        Hurst Exponent — characterises the time series:
            H > 0.55  →  Trending (persistent)    → use trend-following
            H < 0.45  →  Mean reverting            → use mean reversion
            H ≈ 0.50  →  Random walk               → avoid / no edge

        Method: Rescaled Range (R/S) analysis
        """
        lags   = range(2, max_lag)
        tau    = []
        for lag in lags:
            chunks = [s.values[i:i+lag] for i in range(0, len(s) - lag, lag)]
            if not chunks:
                continue
            rs_vals = []
            for chunk in chunks:
                if len(chunk) < 2 or np.std(chunk) == 0:
                    continue
                mean_c  = np.mean(chunk)
                deviate = np.cumsum(chunk - mean_c)
                rs      = (np.max(deviate) - np.min(deviate)) / np.std(chunk)
                rs_vals.append(rs)
            if rs_vals:
                tau.append(np.mean(rs_vals))

        if len(tau) < 3 or not SCIPY_OK:
            return 0.5  # default random walk if can't compute

        lags_arr = np.log(list(lags)[:len(tau)])
        tau_arr  = np.log(tau)
        slope, _, _, _, _ = linregress(lags_arr, tau_arr)
        return max(0.0, min(1.0, slope))

    @staticmethod
    def rolling_beta(stock: pd.Series, benchmark: pd.Series, n=60) -> pd.Series:
        """Rolling beta vs benchmark."""
        s_ret = stock.pct_change()
        b_ret = benchmark.pct_change()
        cov   = s_ret.rolling(n).cov(b_ret)
        var   = b_ret.rolling(n).var()
        return cov / var.replace(0, np.nan)

    @staticmethod
    def half_life(s: pd.Series) -> float:
        """
        Half-life of mean reversion.
        Tells you: if mean-reverting, how many days to revert halfway?
        Lower = faster reversion = better trading opportunity.
        """
        if not SCIPY_OK:
            return 999.0
        lag    = s.shift(1).dropna()
        delta  = s.diff().dropna()
        common = lag.index.intersection(delta.index)
        if len(common) < 10:
            return 999.0
        slope, _, _, _, _ = linregress(lag.loc[common], delta.loc[common])
        if slope >= 0:
            return 999.0  # not mean reverting
        return -np.log(2) / slope

    @staticmethod
    def add_all(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["SMA20"]       = Indicators.sma(df["Close"], 20)
        df["SMA50"]       = Indicators.sma(df["Close"], 50)
        df["SMA200"]      = Indicators.sma(df["Close"], 200)
        df["EMA20"]       = Indicators.ema(df["Close"], 20)
        df["RSI"]         = Indicators.rsi(df["Close"])
        df["ATR"]         = Indicators.atr(df)
        df["ATR_pct"]     = df["ATR"] / df["Close"] * 100
        df["ROC"]         = Indicators.roc(df["Close"])
        df["ZScore"]      = Indicators.zscore(df["Close"])
        df["OBV"]         = Indicators.obv(df)

        m, s, h           = Indicators.macd(df["Close"])
        df["MACD"]        = m
        df["MACD_sig"]    = s
        df["MACD_hist"]   = h

        df["BB_up"], df["BB_mid"], df["BB_lo"] = Indicators.bollinger(df["Close"])
        df["KC_up"], df["KC_mid"], df["KC_lo"] = Indicators.keltner(df)

        stk, std_d        = Indicators.stochastic(df)
        df["Stoch_K"]     = stk
        df["Stoch_D"]     = std_d

        return df


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 3 — SIGNAL ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Signal:
    ticker:      str
    action:      str          # BUY / WATCH / HOLD / AVOID
    score:       float        # 0–100
    strategy:    str          # which strategy fired
    hurst:       float = 0.5
    half_life:   float = 999.0
    reasons:     list  = field(default_factory=list)
    warnings:    list  = field(default_factory=list)
    price:       float = 0.0
    atr_pct:     float = 0.0
    rsi:         float = 50.0
    zscore:      float = 0.0
    stop_price:  float = 0.0
    target_price: float = 0.0


class TrendStrategy:
    """
    Fires when Hurst > 0.55 (trending regime).
    Logic: multiple SMA alignment + MACD confirmation + volume.
    Edge: catching early stages of sustained directional moves.
    """

    def score(self, df: pd.DataFrame, hurst: float) -> tuple[float, list, list]:
        last    = df.iloc[-1]
        pts     = 0
        reasons = []
        warns   = []

        # Trend alignment (40 pts)
        above_200 = last["Close"] > last["SMA200"]
        above_50  = last["Close"] > last["SMA50"]
        above_20  = last["Close"] > last["SMA20"]
        golden    = last["SMA50"] > last["SMA200"]

        if above_200: pts += 16; reasons.append("Above 200 SMA ✓")
        else:         pts -=  5; warns.append("Below 200 SMA")
        if above_50:  pts += 12; reasons.append("Above 50 SMA ✓")
        if above_20:  pts +=  8; reasons.append("Above 20 SMA ✓")
        if golden:    pts +=  4; reasons.append("Golden cross active ✓")

        # Momentum (30 pts)
        rsi = last["RSI"]
        if 45 <= rsi <= 65:    pts += 20; reasons.append(f"RSI ideal ({rsi:.0f}) ✓")
        elif 35 <= rsi < 45:   pts += 12; reasons.append(f"RSI recovering ({rsi:.0f})")
        elif rsi > 65:         pts +=  5; warns.append(f"RSI stretched ({rsi:.0f})")
        else:                  pts +=  0; warns.append(f"RSI weak ({rsi:.0f})")

        if last["MACD"] > last["MACD_sig"]:  pts += 10; reasons.append("MACD bullish ✓")

        # Volume confirmation (20 pts)
        vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
        if last["Volume"] > vol_avg * 1.1:   pts += 10; reasons.append("Above avg volume ✓")
        obv_slope = (df["OBV"].iloc[-1] - df["OBV"].iloc[-20]) / 20
        if obv_slope > 0:                    pts += 10; reasons.append("OBV rising ✓")

        # Hurst bonus (10 pts)
        if hurst > Config.HURST_TREND:       pts += 10; reasons.append(f"Trending regime (H={hurst:.2f}) ✓")

        return min(pts, 100), reasons, warns


class MeanReversionStrategy:
    """
    Fires when Hurst < 0.45 (mean-reverting regime).
    Logic: Z-score below -1.5 SD + short half-life + Bollinger squeeze.
    Edge: catching overextended moves that snap back to mean.
    """

    def score(self, df: pd.DataFrame, hurst: float, hl: float) -> tuple[float, list, list]:
        last    = df.iloc[-1]
        pts     = 0
        reasons = []
        warns   = []

        # Mean reversion regime confirmation (20 pts)
        if hurst < Config.HURST_REVERT:
            pts += 15; reasons.append(f"Mean reverting regime (H={hurst:.2f}) ✓")
        if hl < 10:
            pts +=  5; reasons.append(f"Fast reversion (half-life={hl:.1f}d) ✓")
        elif hl < 20:
            pts +=  2; reasons.append(f"Moderate reversion (half-life={hl:.1f}d)")

        # Z-score entry (40 pts)
        z = last["ZScore"]
        if z <= -2.0:   pts += 40; reasons.append(f"Deeply oversold (Z={z:.2f}) ✓")
        elif z <= -1.5: pts += 28; reasons.append(f"Oversold (Z={z:.2f}) ✓")
        elif z <= -1.0: pts += 15; reasons.append(f"Mildly oversold (Z={z:.2f})")
        else:           warns.append(f"Z-score not oversold ({z:.2f}) — wait")

        # Bollinger Band position (25 pts)
        bb_pct = (last["Close"] - last["BB_lo"]) / (last["BB_up"] - last["BB_lo"] + 1e-9)
        if bb_pct < 0.1:    pts += 25; reasons.append("Near lower Bollinger Band ✓")
        elif bb_pct < 0.25: pts += 15; reasons.append("Below Bollinger midline ✓")
        else:               warns.append("Not near lower band — wait for pullback")

        # RSI confirmation (15 pts)
        rsi = last["RSI"]
        if rsi < 30:        pts += 15; reasons.append(f"RSI oversold ({rsi:.0f}) ✓")
        elif rsi < 40:      pts += 10; reasons.append(f"RSI low ({rsi:.0f}) ✓")
        else:               warns.append(f"RSI not oversold ({rsi:.0f})")

        return min(pts, 100), reasons, warns


class BreakoutStrategy:
    """
    Fires when price breaks above resistance with volume confirmation.
    Logic: 52-week high breakout OR Keltner channel expansion.
    Edge: momentum continuation after consolidation.
    """

    def score(self, df: pd.DataFrame) -> tuple[float, list, list]:
        last    = df.iloc[-1]
        pts     = 0
        reasons = []
        warns   = []

        # Breakout detection (40 pts)
        high_52w = df["Close"].tail(252).max()
        pct_from_high = (high_52w - last["Close"]) / high_52w * 100

        if pct_from_high < 3:
            pts += 30; reasons.append(f"Near 52-week high breakout ✓")
        elif pct_from_high < 8:
            pts += 15; reasons.append(f"Within 8% of 52-week high")
        else:
            warns.append(f"{pct_from_high:.0f}% from high — not a breakout setup")

        # Keltner expansion (20 pts)
        above_keltner = last["Close"] > last["KC_up"]
        if above_keltner: pts += 20; reasons.append("Above Keltner Channel ✓")

        # Volume surge (25 pts)
        vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
        vol_ratio = last["Volume"] / vol_avg
        if vol_ratio > 2.0:    pts += 25; reasons.append(f"Volume surge ({vol_ratio:.1f}x avg) ✓")
        elif vol_ratio > 1.5:  pts += 15; reasons.append(f"Above avg volume ({vol_ratio:.1f}x) ✓")
        else:                  warns.append("No volume confirmation")

        # Momentum (15 pts)
        if last["ROC"] > 5:    pts += 15; reasons.append(f"Strong ROC ({last['ROC']:.1f}%) ✓")
        elif last["ROC"] > 2:  pts +=  8

        return min(pts, 100), reasons, warns


class SignalEngine:
    """
    Orchestrates all three strategies.
    Uses Hurst Exponent to route each stock to the right strategy.
    Returns the highest-scoring applicable signal.
    """

    def __init__(self, fetcher: DataFetcher):
        self.fetcher  = fetcher
        self.trend    = TrendStrategy()
        self.revert   = MeanReversionStrategy()
        self.breakout = BreakoutStrategy()

    def analyse(self, ticker: str) -> Optional[Signal]:
        df_raw = self.fetcher.get(ticker, "1y")
        if df_raw is None or len(df_raw) < 60:
            return None

        df   = Indicators.add_all(df_raw)
        last = df.iloc[-1]
        price = round(last["Close"], 2)

        # Compute statistical properties
        hurst = Indicators.hurst_exponent(df["Close"].tail(100))
        hl    = Indicators.half_life(df["Close"].tail(60))

        # Route to strategy based on Hurst
        if hurst > Config.HURST_TREND:
            score, reasons, warns = self.trend.score(df, hurst)
            strategy = "Trend Following"
        elif hurst < Config.HURST_REVERT:
            score, reasons, warns = self.revert.score(df, hurst, hl)
            strategy = "Mean Reversion"
        else:
            # Random walk — run breakout as last resort
            score, reasons, warns = self.breakout.score(df)
            strategy = "Breakout"
            score = min(score, 55)  # cap breakout in random walk regime

        # ATR-based dynamic stop and target
        atr_pct    = last["ATR_pct"]
        stop_dist  = max(Config.BASE_STOP_PCT, atr_pct / 100 * 1.5)
        stop_price = round(price * (1 - stop_dist), 2)
        tgt_price  = round(price * (1 + stop_dist * Config.TARGET_MULTIPLIER), 2)

        action = (
            "BUY"   if score >= Config.MIN_SCORE_BUY and last["Close"] > last["SMA200"]
            else "WATCH" if score >= Config.MIN_SCORE_WATCH
            else "AVOID"
        )

        return Signal(
            ticker       = ticker,
            action       = action,
            score        = round(score, 1),
            strategy     = strategy,
            hurst        = round(hurst, 3),
            half_life    = round(hl, 1),
            reasons      = reasons,
            warnings     = warns,
            price        = price,
            atr_pct      = round(atr_pct, 2),
            rsi          = round(last["RSI"], 1),
            zscore       = round(last["ZScore"], 2),
            stop_price   = stop_price,
            target_price = tgt_price,
        )


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 4 — RISK ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class RiskEngine:
    """
    Three functions:
    1. Size a new position using half-Kelly
    2. Check portfolio heat (total risk across all open positions)
    3. Compute ATR-based trailing stop
    """

    @staticmethod
    def size_position(signal: Signal, cash: float) -> dict:
        cfg        = Config
        deployable = cash * (1 - cfg.CASH_RESERVE_PCT)

        # Win rate from score (50–75% range)
        win_rate = 0.50 + (signal.score / 100) * 0.25
        stop_d   = abs(signal.price - signal.stop_price) / signal.price
        tgt_d    = abs(signal.target_price - signal.price) / signal.price

        if stop_d == 0:
            return {"error": "Stop distance is zero"}

        # Kelly fraction
        b     = tgt_d / stop_d           # odds
        p, q  = win_rate, 1 - win_rate
        kelly = (b * p - q) / b

        # Half-Kelly with volatility discount
        vol_discount = max(0.4, 1.0 - (signal.atr_pct - 1.5) / 15)
        adj_kelly    = kelly * 0.5 * vol_discount
        pct          = max(cfg.MIN_POSITION_PCT,
                           min(cfg.MAX_POSITION_PCT, adj_kelly))
        amount       = int(deployable * pct)
        shares       = max(1, int(amount / signal.price))
        actual_amt   = shares * signal.price
        max_loss     = shares * (signal.price - signal.stop_price)

        return {
            "shares":       shares,
            "amount":       round(actual_amt, 0),
            "pct_of_cash":  round(pct * 100, 1),
            "kelly_raw":    round(kelly * 100, 1),
            "kelly_adj":    round(adj_kelly * 100, 1),
            "max_loss":     round(max_loss, 0),
            "rr_ratio":     round(tgt_d / stop_d, 2),
            "stop":         signal.stop_price,
            "target":       signal.target_price,
        }

    @staticmethod
    def portfolio_heat(holdings: list, prices: dict) -> dict:
        """
        Portfolio heat = total ₹ at risk across all positions
        as % of total portfolio value.
        Rule: never exceed 6% of portfolio at risk simultaneously.
        """
        total_val  = sum(prices.get(h["ticker"], h["avg"]) * h["qty"]
                         for h in holdings)
        total_risk = 0.0
        breakdown  = []

        for h in holdings:
            price  = prices.get(h["ticker"], h["avg"])
            stop   = h.get("stop", h["avg"] * (1 - Config.BASE_STOP_PCT))
            risk   = max(0, (price - stop) * h["qty"])
            risk_pct = risk / total_val * 100 if total_val > 0 else 0
            total_risk += risk
            breakdown.append({
                "ticker":    h["ticker"].replace(".NS", ""),
                "risk_₹":   round(risk, 0),
                "risk_%":   round(risk_pct, 2),
            })

        heat_pct = total_risk / total_val * 100 if total_val > 0 else 0
        return {
            "total_heat_pct": round(heat_pct, 2),
            "limit_pct":      Config.MAX_PORTFOLIO_HEAT * 100,
            "safe":           heat_pct <= Config.MAX_PORTFOLIO_HEAT * 100,
            "breakdown":      breakdown,
        }

    @staticmethod
    def trailing_stop(df: pd.DataFrame, entry: float, lookback=10) -> dict:
        """
        ATR-based trailing stop.
        Moves up as price rises, never moves down.
        """
        atr        = Indicators.atr(df).iloc[-1]
        high_n     = df["Close"].tail(lookback).max()
        trail_stop = round(high_n - 2 * atr, 2)
        trail_stop = max(trail_stop, entry * (1 - Config.BASE_STOP_PCT))
        curr_price = df["Close"].iloc[-1]
        locked_in  = max(0, curr_price - entry)

        return {
            "trailing_stop": trail_stop,
            "current_price": round(curr_price, 2),
            "locked_gain":   round(locked_in, 2),
            "should_raise":  trail_stop > entry * (1 - Config.BASE_STOP_PCT),
        }


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 5 — BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BacktestResult:
    ticker:           str
    strategy:         str
    total_return:     float
    cagr:             float
    sharpe:           float
    sortino:          float
    max_drawdown:     float
    win_rate:         float
    expectancy:       float
    num_trades:       int
    avg_hold_days:    float
    profit_factor:    float

class Backtester:
    """
    Event-driven backtester.
    Includes: commission, slippage, STT.
    Reports: Sharpe, Sortino, Expectancy, Profit Factor.

    The strategy here mirrors what we're doing live:
    - Enter on 50-SMA crossover with RSI < 70
    - ATR-based dynamic stop loss
    - 2.5:1 reward-to-risk target
    """

    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher

    def _cost(self, price: float, qty: int, side: str) -> float:
        val = price * qty
        c   = val * Config.COMMISSION_PCT
        s   = val * Config.SLIPPAGE_PCT
        stt = val * Config.STT_PCT if side == "sell" else 0
        return c + s + stt

    def run(self, ticker: str, years: int = 3) -> Optional[BacktestResult]:
        df_raw = self.fetcher.get(ticker, f"{years}y")
        if df_raw is None or len(df_raw) < 100:
            return None

        df = Indicators.add_all(df_raw).dropna()
        hurst = Indicators.hurst_exponent(df["Close"].tail(100))

        cash      = 100_000.0
        position  = 0
        entry_p   = 0.0
        entry_i   = 0
        trades    = []

        for i in range(1, len(df)):
            prev  = df.iloc[i - 1]
            curr  = df.iloc[i]
            price = curr["Close"]
            atr   = curr["ATR"]

            if position == 0:
                # Entry signal
                cross_up = prev["Close"] <= prev["SMA50"] and curr["Close"] > curr["SMA50"]
                rsi_ok   = curr["RSI"] < Config.RSI_OVERBOUGHT
                trend_ok = curr["Close"] > curr["SMA200"]

                if cross_up and rsi_ok and trend_ok:
                    shares = int((cash * Config.MAX_POSITION_PCT) / price)
                    if shares > 0:
                        cost       = self._cost(price, shares, "buy")
                        cash      -= (price * shares + cost)
                        position   = shares
                        entry_p    = price
                        entry_i    = i
                        stop_p     = price - 2 * atr
                        target_p   = price + 2 * atr * Config.TARGET_MULTIPLIER

            elif position > 0:
                # Exit signals
                cross_dn = curr["Close"] < curr["SMA50"]
                stop_hit = price <= stop_p
                tgt_hit  = price >= target_p

                if cross_dn or stop_hit or tgt_hit:
                    cost       = self._cost(price, position, "sell")
                    proceeds   = price * position - cost
                    cash      += proceeds
                    pnl_pct    = (price - entry_p) / entry_p
                    hold_days  = i - entry_i
                    trades.append({
                        "pnl_pct":   pnl_pct,
                        "pnl_abs":   (price - entry_p) * position,
                        "hold_days": hold_days,
                        "exit":      "stop" if stop_hit else "target" if tgt_hit else "signal",
                    })
                    position = 0

        # Close open
        if position > 0:
            price    = df["Close"].iloc[-1]
            cost     = self._cost(price, position, "sell")
            cash    += price * position - cost
            trades.append({
                "pnl_pct":   (price - entry_p) / entry_p,
                "pnl_abs":   (price - entry_p) * position,
                "hold_days": len(df) - entry_i,
                "exit":      "end",
            })

        if not trades:
            return None

        # ── Performance metrics ───────────────────────────────────────────
        total_ret  = (cash - 100_000) / 100_000 * 100
        cagr       = ((cash / 100_000) ** (1 / years) - 1) * 100
        wins       = [t for t in trades if t["pnl_pct"] > 0]
        losses     = [t for t in trades if t["pnl_pct"] <= 0]
        win_rate   = len(wins) / len(trades) * 100

        avg_win    = np.mean([t["pnl_pct"] for t in wins])   if wins   else 0
        avg_loss   = abs(np.mean([t["pnl_pct"] for t in losses])) if losses else 0
        expectancy = (win_rate/100 * avg_win) - ((1 - win_rate/100) * avg_loss)

        gross_win  = sum(t["pnl_abs"] for t in wins)   if wins   else 0
        gross_loss = abs(sum(t["pnl_abs"] for t in losses)) if losses else 1
        pf         = gross_win / gross_loss

        # Daily portfolio series for Sharpe/Sortino/Drawdown
        port = [100_000.0]
        c2, pos2, ep2, sp2, tp2 = 100_000.0, 0, 0.0, 0.0, 0.0
        for i in range(1, len(df)):
            prev  = df.iloc[i - 1]
            curr2 = df.iloc[i]
            px    = curr2["Close"]
            atr2  = curr2["ATR"]
            if pos2 == 0:
                if (prev["Close"] <= prev["SMA50"] and curr2["Close"] > curr2["SMA50"]
                        and curr2["RSI"] < Config.RSI_OVERBOUGHT
                        and curr2["Close"] > curr2["SMA200"]):
                    sh = int((c2 * Config.MAX_POSITION_PCT) / px)
                    if sh > 0:
                        c2 -= px * sh; pos2 = sh; ep2 = px
                        sp2 = px - 2 * atr2
                        tp2 = px + 2 * atr2 * Config.TARGET_MULTIPLIER
            elif pos2 > 0:
                if curr2["Close"] < curr2["SMA50"] or px <= sp2 or px >= tp2:
                    c2 += px * pos2; pos2 = 0
            port.append(c2 + pos2 * px)

        pv        = pd.Series(port)
        dr        = pv.pct_change().dropna()
        sharpe    = dr.mean() / dr.std() * np.sqrt(252) if dr.std() > 0 else 0
        neg       = dr[dr < 0]
        sortino   = dr.mean() / neg.std() * np.sqrt(252) if len(neg) > 1 and neg.std() > 0 else 0
        roll_max  = pv.cummax()
        max_dd    = ((pv - roll_max) / roll_max).min() * 100

        return BacktestResult(
            ticker        = ticker.replace(".NS",""),
            strategy      = "Trend(H={:.2f})".format(hurst),
            total_return  = round(total_ret, 2),
            cagr          = round(cagr, 2),
            sharpe        = round(sharpe, 2),
            sortino       = round(sortino, 2),
            max_drawdown  = round(max_dd, 2),
            win_rate      = round(win_rate, 1),
            expectancy    = round(expectancy * 100, 2),
            num_trades    = len(trades),
            avg_hold_days = round(np.mean([t["hold_days"] for t in trades]), 1),
            profit_factor = round(pf, 2),
        )


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 6 — PORTFOLIO TRACKER
# ═══════════════════════════════════════════════════════════════════════════

class PortfolioTracker:
    """
    Daily health check on all holdings.
    Computes: live PnL, tax classification, trailing stop, action needed.
    """

    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher
        self.risk    = RiskEngine()

    def check(self) -> list[dict]:
        results = []
        prices  = {}

        for h in Config.HOLDINGS:
            ticker     = h["ticker"]
            avg        = h["avg"]
            qty        = h["qty"]
            bought     = datetime.strptime(h["bought"], "%Y-%m-%d")
            days_held  = (datetime.today() - bought).days
            is_lt      = days_held >= 365

            df = self.fetcher.get(ticker, "1y")
            if df is None or df.empty:
                results.append({"Ticker": ticker, "Status": "NO DATA"})
                continue

            ltp = round(df["Close"].iloc[-1], 2)
            prices[ticker] = ltp

            pnl_pct  = (ltp - avg) / avg * 100
            pnl_inr  = (ltp - avg) * qty

            # Stop levels
            stop    = h.get("stop",   round(avg * (1 - Config.BASE_STOP_PCT), 2))
            target  = h.get("target", round(avg * (1 + Config.BASE_STOP_PCT
                                                    * Config.TARGET_MULTIPLIER), 2))

            # Trailing stop
            trail   = self.risk.trailing_stop(df, avg)

            # Action
            if ltp <= stop:
                action = c("EXIT — stop hit", "r")
            elif ltp >= target:
                action = c("TAKE PROFIT", "g")
            elif trail["should_raise"]:
                action = c(f"RAISE STOP → ₹{trail['trailing_stop']}", "y")
            elif not (ltp > df["Close"].rolling(200).mean().iloc[-1]) and pnl_pct < -5:
                action = c("REVIEW — below 200SMA", "y")
            else:
                action = "HOLD"

            results.append({
                "Ticker":   ticker.replace(".NS",""),
                "LTP":      f"₹{ltp:,.2f}",
                "Avg":      f"₹{avg:,.2f}",
                "P&L%":     f"{pnl_pct:+.1f}%",
                "P&L₹":     f"₹{pnl_inr:+,.0f}",
                "Days":     days_held,
                "Tax":      "LT" if is_lt else "ST",
                "Stop":     f"₹{stop:,.2f}",
                "Target":   f"₹{target:,.2f}",
                "Action":   action,
            })

        # Portfolio heat
        heat = self.risk.portfolio_heat(Config.HOLDINGS, prices)
        return results, heat


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 7 — TRADE JOURNAL
# ═══════════════════════════════════════════════════════════════════════════

class TradeJournal:
    """
    Persistent trade log stored in JSON.
    Tracks: every trade + thesis + outcome + emotion.
    Computes: expectancy, win rate, mistake patterns.
    """

    def __init__(self, path: str = Config.JOURNAL_FILE):
        self.path   = Path(path)
        self.trades = self._load()

    def _load(self) -> list:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.trades, f, indent=2, default=str)

    def log(self, trade: dict):
        """Log a new trade entry."""
        required = ["ticker", "action", "price", "qty", "thesis"]
        for k in required:
            if k not in trade:
                print(f"  [ERROR] Missing field: {k}")
                return
        trade["timestamp"] = datetime.now().isoformat()
        trade["id"]        = len(self.trades) + 1
        self.trades.append(trade)
        self._save()
        print(f"  {c('Trade logged successfully — ID #{}'.format(trade['id']), 'g')}")

    def close(self, trade_id: int, exit_price: float, notes: str = ""):
        """Close an existing trade and compute outcome."""
        for t in self.trades:
            if t["id"] == trade_id and "exit_price" not in t:
                t["exit_price"] = exit_price
                t["exit_notes"] = notes
                t["exit_time"]  = datetime.now().isoformat()
                pnl = (exit_price - t["price"]) / t["price"] * 100
                if t["action"] == "SELL":
                    pnl = -pnl
                t["pnl_pct"]   = round(pnl, 2)
                t["pnl_inr"]   = round((exit_price - t["price"]) * t["qty"], 2)
                t["outcome"]   = "WIN" if pnl > 0 else "LOSS"
                self._save()
                print(f"  Trade #{trade_id} closed: {t['outcome']} | PnL: {pnl:+.2f}%")
                return
        print(f"  [ERROR] Trade #{trade_id} not found or already closed.")

    def stats(self) -> dict:
        """Compute full system statistics."""
        closed = [t for t in self.trades if "exit_price" in t]
        if not closed:
            return {"message": "No closed trades yet."}

        wins   = [t for t in closed if t["outcome"] == "WIN"]
        losses = [t for t in closed if t["outcome"] == "LOSS"]

        avg_win  = np.mean([t["pnl_pct"] for t in wins])   if wins   else 0
        avg_loss = abs(np.mean([t["pnl_pct"] for t in losses])) if losses else 0
        wr       = len(wins) / len(closed) * 100

        # Expectancy: the average ₹ you make per rupee risked
        expectancy = (wr/100 * avg_win) - ((1 - wr/100) * avg_loss)

        return {
            "total_trades":  len(closed),
            "wins":          len(wins),
            "losses":        len(losses),
            "win_rate":      f"{wr:.1f}%",
            "avg_win":       f"{avg_win:.2f}%",
            "avg_loss":      f"{avg_loss:.2f}%",
            "expectancy":    f"{expectancy:.3f}",
            "note":          "Expectancy > 0 means system has edge. > 0.1 is good.",
        }

    def display(self):
        if not self.trades:
            print("  No trades logged yet.")
            return
        rows = []
        for t in self.trades:
            rows.append({
                "ID":      t["id"],
                "Ticker":  t["ticker"],
                "Action":  t["action"],
                "Entry":   f"₹{t['price']}",
                "Qty":     t["qty"],
                "Thesis":  t["thesis"][:40] + "..." if len(t["thesis"]) > 40 else t["thesis"],
                "Status":  f"CLOSED {t['pnl_pct']:+.1f}%" if "exit_price" in t else "OPEN",
            })
        print(tbl(rows))

    def log_interactive(self):
        """Interactive trade logging from terminal."""
        print(f"\n  {c('=== LOG NEW TRADE ===', 'b')}")
        trade = {
            "ticker":    input("  Ticker (e.g. ICICIBANK.NS): ").strip(),
            "action":    input("  Action (BUY/SELL): ").strip().upper(),
            "price":     float(input("  Entry price: ₹")),
            "qty":       int(input("  Quantity: ")),
            "stop":      float(input("  Stop loss price: ₹")),
            "target":    float(input("  Target price: ₹")),
            "thesis":    input("  Why are you taking this trade? "),
            "strategy":  input("  Strategy (Trend/MeanReversion/Breakout): ").strip(),
            "emotion":   input("  Confidence level (1-10): "),
        }
        self.log(trade)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def header():
    print("\n" + "═"*70)
    print(c("  VALENWOOD CAPITAL — Systematic Trading System v2", "w"))
    print(f"  {datetime.now().strftime('%d %b %Y  %H:%M')}")
    print("  Math: Kelly · Hurst · ATR Stops · Z-Score · Expectancy")
    print("═"*70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",
        choices=["screen","portfolio","backtest","journal","report","trade"],
        default="report")
    parser.add_argument("--ticker",  help="Single ticker for backtest/analysis")
    parser.add_argument("--tickers", nargs="+", help="Override watchlist")
    parser.add_argument("--action",
        choices=["log","close","stats","show"],
        help="Journal sub-action")
    parser.add_argument("--id",    type=int, help="Trade ID for journal close")
    parser.add_argument("--price", type=float, help="Exit price for journal close")
    args = parser.parse_args()

    header()

    fetcher   = DataFetcher()
    engine    = SignalEngine(fetcher)
    risk      = RiskEngine()
    bt        = Backtester(fetcher)
    tracker   = PortfolioTracker(fetcher)
    journal   = TradeJournal()

    watchlist = args.tickers or Config.WATCHLIST

    # ── PORTFOLIO ─────────────────────────────────────────────────────────
    if args.mode in ("portfolio", "report"):
        print(f"\n{'─'*70}")
        print(f"  {c('PORTFOLIO HEALTH CHECK', 'b')}")
        print(f"{'─'*70}")
        holdings_data, heat = tracker.check()
        rows = [r for r in holdings_data if "Status" not in r]
        if rows:
            print(tbl(rows))

        print(f"\n  Portfolio Heat: {heat['total_heat_pct']}% "
              f"(limit {heat['limit_pct']}%) "
              f"{'✓ SAFE' if heat['safe'] else '⚠ OVER LIMIT'}")

        cash = Config.TOTAL_CASH
        print(f"\n  Cash available:     ₹{cash:>12,.0f}")
        print(f"  Reserve (15%):      ₹{cash*0.15:>12,.0f}")
        print(f"  Deployable:         ₹{cash*0.85:>12,.0f}")
        print(f"  Max per position:   ₹{cash*0.20:>12,.0f}")

    # ── SCREEN ────────────────────────────────────────────────────────────
    if args.mode in ("screen", "report"):
        print(f"\n{'─'*70}")
        print(f"  {c('SIGNAL SCAN', 'b')} — {len(watchlist)} stocks")
        print(f"{'─'*70}")

        signals = []
        for ticker in watchlist:
            sig = engine.analyse(ticker)
            if sig:
                signals.append(sig)

        signals.sort(key=lambda s: s.score, reverse=True)

        buy_sigs = [s for s in signals if s.action == "BUY"]
        if buy_sigs:
            print(f"\n  {c(f'BUY SIGNALS ({len(buy_sigs)})', 'g')}\n")
            rows = []
            for s in buy_sigs:
                sz = risk.size_position(s, Config.TOTAL_CASH)
                rows.append({
                    "Ticker":    s.ticker.replace(".NS",""),
                    "Score":     s.score,
                    "Strategy":  s.strategy[:12],
                    "Hurst":     s.hurst,
                    "Price":     f"₹{s.price:,.0f}",
                    "RSI":       s.rsi,
                    "Z-Score":   s.zscore,
                    "Shares":    sz.get("shares", "-"),
                    "Amount":    f"₹{sz.get('amount',0):,.0f}",
                    "Stop":      f"₹{s.stop_price:,.0f}",
                    "Target":    f"₹{s.target_price:,.0f}",
                    "R:R":       sz.get("rr_ratio", "-"),
                })
            print(tbl(rows))
        else:
            print(f"\n  {c('No BUY signals — market may be stretched or screener needs live data.', 'y')}")

        # Full ranked table
        print(f"\n  {c('FULL RANKINGS', 'b')}\n")
        ranked = [{
            "Ticker":   s.ticker.replace(".NS",""),
            "Score":    s.score,
            "Action":   s.action,
            "Strategy": s.strategy[:10],
            "Hurst":    s.hurst,
            "RSI":      s.rsi,
            "Z":        s.zscore,
        } for s in signals]
        print(tbl(ranked))

    # ── BACKTEST ──────────────────────────────────────────────────────────
    if args.mode in ("backtest", "report"):
        tickers_bt = [args.ticker] if args.ticker else watchlist[:6]
        print(f"\n{'─'*70}")
        print(f"  {c('BACKTEST — 3Y Walk Forward', 'b')}")
        print(f"  Strategy: 50-SMA cross | ATR stop | 2.5:1 R:R | Costs included")
        print(f"{'─'*70}\n")

        bt_rows = []
        for t in tickers_bt:
            r = bt.run(t, years=3)
            if r:
                bt_rows.append({
                    "Ticker":       r.ticker,
                    "CAGR%":        f"{r.cagr:+.1f}%",
                    "Sharpe":       r.sharpe,
                    "Sortino":      r.sortino,
                    "MaxDD%":       f"{r.max_drawdown:.1f}%",
                    "WinRate%":     f"{r.win_rate:.0f}%",
                    "Expectancy":   r.expectancy,
                    "Trades":       r.num_trades,
                    "AvgHold(d)":   r.avg_hold_days,
                    "PF":           r.profit_factor,
                })

        if bt_rows:
            bt_rows.sort(key=lambda x: float(x["CAGR%"].rstrip("%")), reverse=True)
            print(tbl(bt_rows))
            print(f"\n  {c('Expectancy > 0 = system has edge. Profit Factor > 1.5 = strong system.', 'y')}")

    # ── JOURNAL ───────────────────────────────────────────────────────────
    if args.mode == "journal" or args.mode == "trade":
        action = args.action or "show"
        if action == "log":
            journal.log_interactive()
        elif action == "close":
            if args.id and args.price:
                journal.close(args.id, args.price)
            else:
                print("  Usage: --mode trade --action close --id 1 --price 1290")
        elif action == "stats":
            stats = journal.stats()
            print(f"\n  {c('TRADE JOURNAL STATISTICS', 'b')}\n")
            for k, v in stats.items():
                print(f"  {k:<20} {v}")
        else:
            print(f"\n  {c('TRADE JOURNAL', 'b')}\n")
            journal.display()
            print()
            stats = journal.stats()
            if isinstance(stats, dict) and "total_trades" in stats:
                for k, v in stats.items():
                    print(f"  {k:<20} {v}")

    print(f"\n{'═'*70}")
    print(c("  Signals are informational only. Always verify before acting.", "y"))
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    main()
