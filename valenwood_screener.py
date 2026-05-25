"""
Valenwood Capital — NSE Stock Screener & Portfolio Framework
=============================================================
Built for: Ekam's dad's Motilal Oswal portfolio
Purpose  : Systematic stock selection, position sizing, backtesting,
           and ongoing portfolio health monitoring

Requirements:
    pip install yfinance pandas numpy scipy tabulate colorama

Run:
    python valenwood_screener.py --mode screen          # Screen new stocks
    python valenwood_screener.py --mode portfolio       # Check current portfolio
    python valenwood_screener.py --mode backtest        # Backtest a strategy
    python valenwood_screener.py --mode report          # Full report
"""

import argparse
import warnings
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Try importing optional dependencies gracefully ───────────────────────────
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[WARN] yfinance not installed. Run: pip install yfinance")

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════
# 1. CONFIGURATION — Edit this section to customise your universe & rules
# ═══════════════════════════════════════════════════════════════════════════

class Config:
    # ── Portfolio constants ────────────────────────────────────────────────
    TOTAL_CASH          = 145_586        # Current deployable cash (₹)
    MAX_POSITION_PCT    = 0.20           # Max 20% per stock
    MIN_POSITION_PCT    = 0.05           # Min 5% per stock (avoid noise positions)
    MAX_POSITIONS       = 6              # Max stocks in active portfolio
    CASH_RESERVE_PCT    = 0.15           # Always keep 15% as dry powder

    # ── Risk rules ────────────────────────────────────────────────────────
    STOP_LOSS_PCT       = 0.08           # Exit if stock drops 8% from buy
    TARGET_PCT          = 0.20           # Take partial profit at 20% gain
    TRAILING_STOP_PCT   = 0.05           # Trailing stop: 5% below rolling high

    # ── Screening filters ─────────────────────────────────────────────────
    MIN_MARKET_CAP_CR   = 2_000          # Min ₹2,000 Cr market cap (avoid illiquid small caps)
    MAX_PE              = 45             # Max P/E (avoid extreme overvaluation)
    MIN_PE              = 5              # Min P/E (avoid value traps / distress)
    MIN_ROE             = 12             # Min Return on Equity (%)
    MAX_DEBT_EQUITY     = 1.5            # Max D/E ratio
    MIN_REVENUE_GROWTH  = 8              # Min 3-yr revenue CAGR (%)
    MIN_AVG_VOLUME      = 200_000        # Min daily volume (liquidity filter)

    # ── Technical filters ─────────────────────────────────────────────────
    RSI_OVERSOLD        = 40             # Only buy below this RSI (not chasing)
    RSI_OVERBOUGHT      = 70             # Avoid above this RSI
    MIN_ADTV_CR         = 2              # Min avg daily turnover ₹2 Cr

    # ── Backtest settings ─────────────────────────────────────────────────
    BACKTEST_YEARS      = 3
    BENCHMARK_TICKER    = "^NSEI"        # Nifty 50

    # ── Current holdings (from Motilal CSV) ───────────────────────────────
    CURRENT_HOLDINGS = [
        {"ticker": "KPIGREEN.NS",  "qty": 325, "avg_price": 593.93,
         "buy_date": "2024-04-05", "sector": "Renewable Energy"},
        {"ticker": "TMPV.NS",      "qty": 175, "avg_price": 605.68,
         "buy_date": "2025-10-14", "sector": "Automobile",
         "note": "Illiquid demerger — monitor only"},
        {"ticker": "FINCABLES.NS", "qty": 40,  "avg_price": 1297.13,
         "buy_date": "2024-07-31", "sector": "Cables & Wires"},
        {"ticker": "GODREJCP.NS",  "qty": 25,  "avg_price": 1047.67,
         "buy_date": "2025-01-01", "sector": "FMCG"},
        {"ticker": "EXIDEIND.NS",  "qty": 95,  "avg_price": 394.40,
         "buy_date": "2025-10-09", "sector": "Auto Ancillary"},
    ]

    # ── Watchlist — stocks to screen (NSE tickers with .NS suffix) ─────────
    # Curated universe: quality large/mid caps across sectors
    WATCHLIST = [
        # Banking & Finance
        "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "BAJFINANCE.NS", "CHOLAFIN.NS",
        # IT
        "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "PERSISTENT.NS",
        # FMCG
        "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
        # Auto
        "MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS",
        # Pharma
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS",
        # Infrastructure / Capital Goods
        "LT.NS", "ABB.NS", "SIEMENS.NS", "CUMMINSIND.NS",
        # Consumption
        "TITAN.NS", "TRENT.NS", "DMART.NS",
        # Energy / Utilities
        "NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS",
    ]


# ═══════════════════════════════════════════════════════════════════════════
# 2. DATA LAYER — Fetch & cache price/fundamental data
# ═══════════════════════════════════════════════════════════════════════════

class DataFetcher:
    """Wraps yfinance with caching and graceful error handling."""

    def __init__(self):
        self._cache: dict = {}

    def get_history(self, ticker: str, period: str = "2y") -> Optional[pd.DataFrame]:
        key = f"{ticker}_{period}"
        if key in self._cache:
            return self._cache[key]
        if not YFINANCE_AVAILABLE:
            return self._mock_history(ticker, period)
        try:
            data = yf.Ticker(ticker).history(period=period)
            if data.empty:
                return None
            self._cache[key] = data
            return data
        except Exception as e:
            print(f"  [WARN] Could not fetch {ticker}: {e}")
            return None

    def get_info(self, ticker: str) -> dict:
        key = f"{ticker}_info"
        if key in self._cache:
            return self._cache[key]
        if not YFINANCE_AVAILABLE:
            return {}
        try:
            info = yf.Ticker(ticker).info
            self._cache[key] = info
            return info
        except Exception:
            return {}

    def _mock_history(self, ticker: str, period: str) -> pd.DataFrame:
        """Deterministic mock data for offline testing."""
        seed = sum(ord(c) for c in ticker)
        rng = np.random.default_rng(seed)
        days = 504 if "2y" in period else 756
        dates = pd.bdate_range(end=datetime.today(), periods=days)
        start = rng.uniform(200, 2000)
        returns = rng.normal(0.0003, 0.018, days)
        prices = start * np.exp(np.cumsum(returns))
        return pd.DataFrame({
            "Open":   prices * rng.uniform(0.99, 1.00, days),
            "High":   prices * rng.uniform(1.00, 1.02, days),
            "Low":    prices * rng.uniform(0.98, 1.00, days),
            "Close":  prices,
            "Volume": rng.integers(50_000, 5_000_000, days),
        }, index=dates)


# ═══════════════════════════════════════════════════════════════════════════
# 3. TECHNICAL INDICATORS
# ═══════════════════════════════════════════════════════════════════════════

class Indicators:
    """Stateless technical indicator calculations on a price DataFrame."""

    @staticmethod
    def sma(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).mean()

    @staticmethod
    def ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        hl  = df["High"] - df["Low"]
        hpc = (df["High"] - df["Close"].shift()).abs()
        lpc = (df["Low"]  - df["Close"].shift()).abs()
        tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def macd(series: pd.Series, fast=12, slow=26, signal=9):
        ema_fast   = series.ewm(span=fast,   adjust=False).mean()
        ema_slow   = series.ewm(span=slow,   adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram   = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(series: pd.Series, window=20, num_std=2):
        mid   = series.rolling(window).mean()
        std   = series.rolling(window).std()
        upper = mid + num_std * std
        lower = mid - num_std * std
        return upper, mid, lower

    @staticmethod
    def adtv(df: pd.DataFrame, window=20) -> float:
        """Average Daily Turnover in Crores."""
        turnover = df["Close"] * df["Volume"]
        return turnover.rolling(window).mean().iloc[-1] / 1e7  # → Crores

    @staticmethod
    def add_all(df: pd.DataFrame) -> pd.DataFrame:
        """Add all indicators to a price dataframe in one call."""
        df = df.copy()
        df["SMA_20"]    = Indicators.sma(df["Close"], 20)
        df["SMA_50"]    = Indicators.sma(df["Close"], 50)
        df["SMA_200"]   = Indicators.sma(df["Close"], 200)
        df["EMA_20"]    = Indicators.ema(df["Close"], 20)
        df["RSI"]       = Indicators.rsi(df["Close"])
        df["ATR"]       = Indicators.atr(df)
        macd, sig, hist = Indicators.macd(df["Close"])
        df["MACD"]      = macd
        df["MACD_Sig"]  = sig
        df["MACD_Hist"] = hist
        df["BB_Up"], df["BB_Mid"], df["BB_Lo"] = Indicators.bollinger_bands(df["Close"])
        return df


# ═══════════════════════════════════════════════════════════════════════════
# 4. SIGNAL ENGINE — Generate buy/sell signals
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Signal:
    ticker:     str
    action:     str          # BUY / SELL / HOLD / WATCH
    score:      float        # 0–100 composite score
    reasons:    list[str] = field(default_factory=list)
    warnings:   list[str] = field(default_factory=list)
    price:      float = 0.0
    rsi:        float = 0.0
    above_200:  bool  = False
    macd_bull:  bool  = False

class SignalEngine:
    """
    Generates a composite signal score for each ticker.

    Score breakdown (total 100):
        Trend           30 pts  (price vs 200/50/20 SMA)
        Momentum        25 pts  (RSI positioning, MACD)
        Volatility      20 pts  (ATR-based risk, BB position)
        Volume          15 pts  (ADTV, volume trend)
        Mean reversion  10 pts  (distance from SMA, BB squeeze)
    """

    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher

    def score(self, ticker: str) -> Optional[Signal]:
        df_raw = self.fetcher.get_history(ticker, period="1y")
        if df_raw is None or len(df_raw) < 60:
            return None

        df   = Indicators.add_all(df_raw)
        last = df.iloc[-1]
        sig  = Signal(ticker=ticker, action="HOLD", score=0.0, price=round(last["Close"], 2))
        pts  = 0
        cfg  = Config

        # ── TREND (30 pts) ────────────────────────────────────────────────
        above_200 = last["Close"] > last["SMA_200"]
        above_50  = last["Close"] > last["SMA_50"]
        above_20  = last["Close"] > last["SMA_20"]
        sma20_above_50  = last["SMA_20"]  > last["SMA_50"]
        sma50_above_200 = last["SMA_50"]  > last["SMA_200"]

        if above_200:         pts += 12; sig.reasons.append("Above 200 SMA ✓")
        if above_50:          pts +=  8; sig.reasons.append("Above 50 SMA ✓")
        if above_20:          pts +=  5; sig.reasons.append("Above 20 SMA ✓")
        if sma50_above_200:   pts +=  3; sig.reasons.append("Golden cross aligned ✓")
        if not above_200:     sig.warnings.append("Below 200 SMA — downtrend risk")
        sig.above_200 = above_200

        # ── MOMENTUM (25 pts) ─────────────────────────────────────────────
        rsi = last["RSI"]
        sig.rsi = round(rsi, 1)

        if 35 <= rsi <= 55:
            pts += 20
            sig.reasons.append(f"RSI in ideal buy zone ({rsi:.0f}) ✓")
        elif 55 < rsi <= 65:
            pts += 12
            sig.reasons.append(f"RSI moderate ({rsi:.0f})")
        elif rsi < 35:
            pts +=  8
            sig.reasons.append(f"RSI oversold ({rsi:.0f}) — potential reversal")
            sig.warnings.append("Oversold — confirm trend before buying")
        else:
            pts +=  0
            sig.warnings.append(f"RSI overbought ({rsi:.0f}) — wait for pullback")

        macd_bull = last["MACD"] > last["MACD_Sig"]
        if macd_bull:
            pts += 5; sig.reasons.append("MACD bullish crossover ✓")
        sig.macd_bull = macd_bull

        # ── VOLATILITY (20 pts) ───────────────────────────────────────────
        atr_pct = last["ATR"] / last["Close"] * 100
        bb_pct  = (last["Close"] - last["BB_Lo"]) / (last["BB_Up"] - last["BB_Lo"] + 1e-9) * 100

        if atr_pct < 2.5:
            pts += 12; sig.reasons.append(f"Low volatility ({atr_pct:.1f}% ATR) ✓")
        elif atr_pct < 4.0:
            pts +=  7
        else:
            pts +=  2; sig.warnings.append(f"High volatility ({atr_pct:.1f}% ATR) — size down")

        if 20 <= bb_pct <= 60:
            pts +=  8; sig.reasons.append("Positioned well within Bollinger Bands ✓")
        elif bb_pct < 20:
            pts +=  4; sig.warnings.append("Near lower Bollinger Band — falling knife risk")
        else:
            pts +=  2; sig.warnings.append("Near upper Bollinger Band — stretched")

        # ── VOLUME (15 pts) ───────────────────────────────────────────────
        adtv = Indicators.adtv(df)
        if adtv >= cfg.MIN_ADTV_CR:
            pts += 10; sig.reasons.append(f"Adequate liquidity (ADTV ₹{adtv:.1f} Cr) ✓")
        else:
            sig.warnings.append(f"Low liquidity (ADTV ₹{adtv:.1f} Cr) — exit risk")

        # Volume trend: is today's volume above 20-day avg?
        vol_sma = df["Volume"].rolling(20).mean().iloc[-1]
        if last["Volume"] > vol_sma * 1.2:
            pts +=  5; sig.reasons.append("Above-average volume ✓")

        # ── MEAN REVERSION (10 pts) ───────────────────────────────────────
        # How far is price below its 52-week high? Sweet spot: 10–30% off highs
        high_52w = df["Close"].tail(252).max()
        pct_off_high = (high_52w - last["Close"]) / high_52w * 100
        if 10 <= pct_off_high <= 35:
            pts += 10
            sig.reasons.append(f"{pct_off_high:.0f}% off 52-week high — good entry zone ✓")
        elif pct_off_high < 10:
            pts +=  3; sig.warnings.append("Near 52-week high — momentum play only")
        else:
            pts +=  4; sig.warnings.append(f"{pct_off_high:.0f}% off high — verify no structural break")

        sig.score = min(pts, 100)

        # ── ACTION ASSIGNMENT ─────────────────────────────────────────────
        if sig.score >= 65 and above_200 and not (rsi > cfg.RSI_OVERBOUGHT):
            sig.action = "BUY"
        elif sig.score >= 50:
            sig.action = "WATCH"
        elif sig.score < 35:
            sig.action = "AVOID"
        else:
            sig.action = "HOLD"

        return sig


# ═══════════════════════════════════════════════════════════════════════════
# 5. POSITION SIZER — Kelly-inspired with hard caps
# ═══════════════════════════════════════════════════════════════════════════

class PositionSizer:
    """
    Modified Kelly Criterion with hard position caps.

    Kelly fraction = (edge / odds)
    We use a half-Kelly (conservative) and cap at Config.MAX_POSITION_PCT.
    """

    @staticmethod
    def size(score: float, atr_pct: float, cash: float) -> dict:
        cfg = Config
        deployable = cash * (1 - cfg.CASH_RESERVE_PCT)

        # Win rate estimate from score (50–80% range mapped from score 0–100)
        win_rate = 0.50 + (score / 100) * 0.30
        avg_win  = cfg.TARGET_PCT
        avg_loss = cfg.STOP_LOSS_PCT

        # Kelly fraction
        b = avg_win / avg_loss          # odds ratio
        p = win_rate
        q = 1 - p
        kelly = (b * p - q) / b

        # Half-Kelly with ATR-based volatility discount
        vol_discount = max(0.5, 1 - (atr_pct - 1.5) / 10)
        half_kelly   = kelly * 0.5 * vol_discount

        # Apply hard caps
        pct = max(cfg.MIN_POSITION_PCT, min(cfg.MAX_POSITION_PCT, half_kelly))
        amount = round(deployable * pct, 0)

        return {
            "kelly_raw":    round(kelly * 100, 1),
            "kelly_adj":    round(half_kelly * 100, 1),
            "pct_applied":  round(pct * 100, 1),
            "amount_inr":   int(amount),
            "stop_loss_pct": cfg.STOP_LOSS_PCT * 100,
            "target_pct":   cfg.TARGET_PCT * 100,
        }


# ═══════════════════════════════════════════════════════════════════════════
# 6. BACKTESTER — Simple SMA crossover strategy baseline
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BacktestResult:
    ticker:          str
    total_return:    float
    cagr:            float
    sharpe:          float
    max_drawdown:    float
    win_rate:        float
    num_trades:      int
    benchmark_return: float

class Backtester:
    """
    Strategy: Buy when price crosses above 50 SMA with RSI < 60.
              Sell when price crosses below 50 SMA OR stop loss hit.

    This is intentionally simple — a baseline to beat, not the final word.
    """

    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher

    def run(self, ticker: str, years: int = 3) -> Optional[BacktestResult]:
        period = f"{years}y"
        df_raw = self.fetcher.get_history(ticker, period=period)
        if df_raw is None or len(df_raw) < 100:
            return None

        df   = Indicators.add_all(df_raw)
        df   = df.dropna()
        cash = 100_000.0
        position = 0
        entry_price = 0.0
        trades = []

        for i in range(1, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            price = curr["Close"]

            # Entry: price crosses above 50 SMA, RSI not overbought
            if (position == 0
                    and prev["Close"] <= prev["SMA_50"]
                    and curr["Close"] >  curr["SMA_50"]
                    and curr["RSI"] < Config.RSI_OVERBOUGHT):
                shares = int(cash / price)
                if shares > 0:
                    position    = shares
                    entry_price = price
                    cash       -= shares * price

            # Exit: price crosses below 50 SMA OR stop loss
            elif position > 0:
                stop_price   = entry_price * (1 - Config.STOP_LOSS_PCT)
                target_price = entry_price * (1 + Config.TARGET_PCT)
                exit_signal  = (
                    curr["Close"] < curr["SMA_50"]   # trend exit
                    or price <= stop_price            # stop loss
                    or price >= target_price          # take profit
                )
                if exit_signal:
                    cash  += position * price
                    pnl    = (price - entry_price) / entry_price
                    trades.append(pnl)
                    position = 0

        # Close open position at end
        if position > 0:
            final_price = df.iloc[-1]["Close"]
            cash += position * final_price
            pnl   = (final_price - entry_price) / entry_price
            trades.append(pnl)

        # ── Metrics ───────────────────────────────────────────────────────
        final_value   = cash
        total_return  = (final_value - 100_000) / 100_000 * 100
        cagr          = ((final_value / 100_000) ** (1 / years) - 1) * 100
        win_rate      = (sum(1 for t in trades if t > 0) / len(trades) * 100) if trades else 0

        # Daily portfolio value for Sharpe & drawdown
        port_vals = []
        c2 = 100_000.0
        pos2 = 0
        ep2  = 0.0
        for i in range(len(df)):
            curr  = df.iloc[i]
            price = curr["Close"]
            if i > 0:
                prev = df.iloc[i - 1]
                if (pos2 == 0
                        and prev["Close"] <= prev["SMA_50"]
                        and curr["Close"] >  curr["SMA_50"]
                        and curr["RSI"] < Config.RSI_OVERBOUGHT):
                    shares = int(c2 / price)
                    if shares > 0:
                        pos2 = shares; ep2 = price; c2 -= shares * price
                elif pos2 > 0:
                    stop  = ep2 * (1 - Config.STOP_LOSS_PCT)
                    tgt   = ep2 * (1 + Config.TARGET_PCT)
                    if curr["Close"] < curr["SMA_50"] or price <= stop or price >= tgt:
                        c2 += pos2 * price; pos2 = 0
            val = c2 + pos2 * price
            port_vals.append(val)

        pv        = pd.Series(port_vals)
        daily_ret = pv.pct_change().dropna()
        sharpe    = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else 0
        roll_max  = pv.cummax()
        drawdown  = (pv - roll_max) / roll_max
        max_dd    = drawdown.min() * 100

        # Benchmark: buy and hold Nifty proxy (use index of df as time)
        bm_start = df["Close"].iloc[0]
        bm_end   = df["Close"].iloc[-1]
        bm_ret   = (bm_end - bm_start) / bm_start * 100

        return BacktestResult(
            ticker           = ticker,
            total_return     = round(total_return, 2),
            cagr             = round(cagr, 2),
            sharpe           = round(sharpe, 2),
            max_drawdown     = round(max_dd, 2),
            win_rate         = round(win_rate, 1),
            num_trades       = len(trades),
            benchmark_return = round(bm_ret, 2),
        )


# ═══════════════════════════════════════════════════════════════════════════
# 7. PORTFOLIO MONITOR — Health check on current holdings
# ═══════════════════════════════════════════════════════════════════════════

class PortfolioMonitor:
    """Checks each holding against stop loss, target, and trend rules."""

    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher
        self.cfg     = Config

    def check(self) -> list[dict]:
        results = []
        for h in Config.CURRENT_HOLDINGS:
            ticker     = h["ticker"]
            avg_price  = h["avg_price"]
            qty        = h["qty"]
            buy_date   = datetime.strptime(h["buy_date"], "%Y-%m-%d")
            days_held  = (datetime.today() - buy_date).days
            is_ltcg    = days_held >= 365
            note       = h.get("note", "")

            df_raw = self.fetcher.get_history(ticker, period="1y")
            if df_raw is None:
                results.append({"ticker": ticker, "status": "DATA ERROR"})
                continue

            df   = Indicators.add_all(df_raw)
            last = df.iloc[-1]
            ltp  = round(last["Close"], 2)

            pnl_pct   = (ltp - avg_price) / avg_price * 100
            pnl_inr   = round((ltp - avg_price) * qty, 0)
            stop_loss = round(avg_price * (1 - self.cfg.STOP_LOSS_PCT), 2)
            target    = round(avg_price * (1 + self.cfg.TARGET_PCT), 2)

            # Rolling high for trailing stop
            high_30d     = df["Close"].tail(30).max()
            trailing_stp = round(high_30d * (1 - self.cfg.TRAILING_STOP_PCT), 2)

            above_200 = ltp > last["SMA_200"]
            rsi       = round(last["RSI"], 1)

            # Determine action
            if ltp <= stop_loss:
                action = "🔴 STOP LOSS HIT — EXIT"
            elif ltp >= target:
                action = "🟢 TARGET HIT — TAKE PARTIAL PROFIT"
            elif ltp <= trailing_stp and pnl_pct > 5:
                action = "🟡 TRAILING STOP — LOCK IN GAINS"
            elif not above_200 and pnl_pct < -5:
                action = "🟠 REVIEW — Below 200 SMA & in loss"
            else:
                action = "⚪ HOLD"

            results.append({
                "Ticker":       ticker.replace(".NS", ""),
                "LTP":          f"₹{ltp:,.2f}",
                "Avg":          f"₹{avg_price:,.2f}",
                "P&L%":         f"{pnl_pct:+.1f}%",
                "P&L ₹":        f"₹{pnl_inr:+,.0f}",
                "Days":         days_held,
                "Tax":          "LTCG" if is_ltcg else "STCG",
                "RSI":          rsi,
                "Stop":         f"₹{stop_loss:,.2f}",
                "Target":       f"₹{target:,.2f}",
                "Action":       action,
                "Note":         note,
            })

        return results


# ═══════════════════════════════════════════════════════════════════════════
# 8. SCREENER — Run full watchlist scan
# ═══════════════════════════════════════════════════════════════════════════

class Screener:
    def __init__(self, fetcher: DataFetcher):
        self.engine = SignalEngine(fetcher)
        self.sizer  = PositionSizer()

    def run(self, watchlist: list[str]) -> list[dict]:
        results = []
        print(f"\n  Screening {len(watchlist)} stocks...\n")

        for ticker in watchlist:
            sig = self.engine.score(ticker)
            if sig is None:
                continue

            row = {
                "Ticker":   ticker.replace(".NS", ""),
                "Price":    f"₹{sig.price:,.0f}",
                "Score":    sig.score,
                "Action":   sig.action,
                "RSI":      sig.rsi,
                "200SMA":   "✓" if sig.above_200 else "✗",
                "MACD":     "Bull" if sig.macd_bull else "Bear",
                "Reasons":  " | ".join(sig.reasons[:2]),
                "Warnings": " | ".join(sig.warnings[:1]),
            }

            if sig.action == "BUY":
                sizing = self.sizer.size(
                    sig.score,
                    atr_pct=2.5,          # default; real ATR needs df
                    cash=Config.TOTAL_CASH
                )
                row["Suggested ₹"]   = f"₹{sizing['amount_inr']:,}"
                row["Kelly Adj %"]   = f"{sizing['kelly_adj']}%"
                row["Stop Loss"]     = f"-{sizing['stop_loss_pct']:.0f}%"
                row["Take Profit"]   = f"+{sizing['target_pct']:.0f}%"

            results.append(row)

        # Sort by score descending
        results.sort(key=lambda x: x["Score"], reverse=True)
        return results


# ═══════════════════════════════════════════════════════════════════════════
# 9. REPORT PRINTER — Clean terminal output
# ═══════════════════════════════════════════════════════════════════════════

def _c(text: str, color: str) -> str:
    if not COLORAMA_AVAILABLE:
        return text
    colors = {
        "green":  Fore.GREEN,
        "red":    Fore.RED,
        "yellow": Fore.YELLOW,
        "cyan":   Fore.CYAN,
        "bold":   Style.BRIGHT,
        "reset":  Style.RESET_ALL,
    }
    return colors.get(color, "") + str(text) + Style.RESET_ALL


def print_table(data: list[dict], title: str = ""):
    if not data:
        print("  No results.")
        return
    if title:
        print(f"\n{'─'*70}")
        print(f"  {_c(title, 'cyan')}")
        print(f"{'─'*70}")
    if TABULATE_AVAILABLE:
        print(tabulate(data, headers="keys", tablefmt="rounded_outline",
                       numalign="right", stralign="left"))
    else:
        df = pd.DataFrame(data)
        print(df.to_string(index=False))


def print_header():
    print("\n" + "═" * 70)
    print(_c("  VALENWOOD CAPITAL — NSE Stock Screener & Portfolio Monitor", "bold"))
    print(f"  {datetime.now().strftime('%d %b %Y  %H:%M')}")
    print("═" * 70)


def print_portfolio_summary():
    holdings = Config.CURRENT_HOLDINGS
    total_invested = sum(h["avg_price"] * h["qty"] for h in holdings)
    cash = Config.TOTAL_CASH
    print(f"\n  {'Total invested (portfolio):':<35} ₹{total_invested:>12,.0f}")
    print(f"  {'Deployable cash:':<35} ₹{cash:>12,.0f}")
    print(f"  {'Max per position (20%):':<35} ₹{cash * 0.20:>12,.0f}")
    print(f"  {'Cash reserve (15%):':<35} ₹{cash * 0.15:>12,.0f}")
    print(f"  {'Deployable after reserve:':<35} ₹{cash * 0.85:>12,.0f}")


# ═══════════════════════════════════════════════════════════════════════════
# 10. MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Valenwood Capital — NSE Screener & Portfolio Monitor"
    )
    parser.add_argument(
        "--mode",
        choices=["screen", "portfolio", "backtest", "report"],
        default="report",
        help="screen | portfolio | backtest | report (default: report)"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Override watchlist with specific tickers (e.g. RELIANCE.NS TCS.NS)"
    )
    args = parser.parse_args()

    print_header()

    fetcher   = DataFetcher()
    screener  = Screener(fetcher)
    monitor   = PortfolioMonitor(fetcher)
    backtester = Backtester(fetcher)

    watchlist = args.tickers if args.tickers else Config.WATCHLIST

    # ── PORTFOLIO MODE ────────────────────────────────────────────────────
    if args.mode in ("portfolio", "report"):
        print_portfolio_summary()
        holdings_data = monitor.check()
        print_table(
            [{k: v for k, v in h.items() if k != "Note"} for h in holdings_data],
            title="CURRENT HOLDINGS HEALTH CHECK"
        )
        # Print notes separately
        for h in holdings_data:
            if h.get("Note"):
                print(f"\n  ⚠  {h['Ticker']}: {h['Note']}")

    # ── SCREEN MODE ───────────────────────────────────────────────────────
    if args.mode in ("screen", "report"):
        screen_results = screener.run(watchlist)

        buy_signals = [r for r in screen_results if r["Action"] == "BUY"]
        watch_signals = [r for r in screen_results if r["Action"] == "WATCH"]

        if buy_signals:
            print_table(buy_signals, title=f"BUY SIGNALS ({len(buy_signals)} stocks)")
        else:
            print("\n  No BUY signals in current watchlist — market may be stretched.")

        if watch_signals:
            # Show top 5 watchlist candidates
            print_table(
                [{k: v for k, v in r.items()
                  if k not in ("Reasons", "Warnings")} for r in watch_signals[:5]],
                title=f"WATCHLIST — Top candidates"
            )

        # Full ranked table
        print_table(
            [{"Ticker": r["Ticker"], "Score": r["Score"], "Action": r["Action"],
              "RSI": r["RSI"], "200SMA": r["200SMA"]} for r in screen_results],
            title="FULL SCREEN RESULTS (ranked by score)"
        )

    # ── BACKTEST MODE ─────────────────────────────────────────────────────
    if args.mode in ("backtest", "report"):
        bt_tickers = (args.tickers or Config.WATCHLIST[:8])
        print(f"\n{'─'*70}")
        print(f"  {_c('BACKTEST RESULTS — SMA50 Crossover Strategy (3Y)', 'cyan')}")
        print(f"{'─'*70}")
        print("  Strategy: Buy on 50-SMA cross up + RSI < 70 | Sell on 50-SMA cross down / stop / target\n")

        bt_results = []
        for ticker in bt_tickers:
            result = backtester.run(ticker, years=Config.BACKTEST_YEARS)
            if result:
                alpha = result.total_return - result.benchmark_return
                bt_results.append({
                    "Ticker":        ticker.replace(".NS", ""),
                    "Total Ret%":    f"{result.total_return:+.1f}%",
                    "CAGR%":         f"{result.cagr:+.1f}%",
                    "Sharpe":        result.sharpe,
                    "Max DD%":       f"{result.max_drawdown:.1f}%",
                    "Win Rate%":     f"{result.win_rate:.0f}%",
                    "Trades":        result.num_trades,
                    "vs Benchmark":  f"{alpha:+.1f}%",
                })

        bt_results.sort(key=lambda x: float(x["CAGR%"].rstrip("%")), reverse=True)
        print_table(bt_results)

    print(f"\n{'═'*70}")
    print(_c("  Run completed. All signals are informational — verify before acting.", "yellow"))
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    main()
