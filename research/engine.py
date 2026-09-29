"""EURUSD M5 statistical mean-reversion research engine.

Closed-bar signals only. Costs applied as round-turn pips converted to R.
HistData M1 bid OHLC is resampled to M5. Timestamps are US Eastern as published
by HistData (traditionally EST, UTC-5; session clocks use the data's wall time).
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from numba import njit

PIP = 0.0001
DATA_ROOT = os.path.join(os.path.dirname(__file__), "data")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_m1_frames(root: str = DATA_ROOT) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(root, "**", "DAT_ASCII_EURUSD_M1_*.csv"), recursive=True))
    if not files:
        raise FileNotFoundError(f"No HistData CSVs under {root}")
    frames = []
    for path in files:
        df = pd.read_csv(
            path,
            sep=";",
            header=None,
            names=["ts", "open", "high", "low", "close", "volume"],
            dtype={"ts": str, "open": np.float64, "high": np.float64, "low": np.float64, "close": np.float64, "volume": np.float64},
        )
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["time"] = pd.to_datetime(out["ts"], format="%Y%m%d %H%M%S")
    out = out.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    return out


def resample_m5(m1: pd.DataFrame) -> pd.DataFrame:
    g = m1.set_index("time").resample("5min", label="left", closed="left")
    m5 = g.agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    m5 = m5.reset_index()
    return m5


def bars_to_arrays(m5: pd.DataFrame) -> dict:
    t = m5["time"].to_numpy()
    return {
        "time": t,
        "open": m5["open"].to_numpy(np.float64),
        "high": m5["high"].to_numpy(np.float64),
        "low": m5["low"].to_numpy(np.float64),
        "close": m5["close"].to_numpy(np.float64),
        "hour": m5["time"].dt.hour.to_numpy(np.int32),
        "minute": m5["time"].dt.minute.to_numpy(np.int32),
        "dow": m5["time"].dt.dayofweek.to_numpy(np.int32),  # Mon=0
        "year": m5["time"].dt.year.to_numpy(np.int32),
        "month": m5["time"].dt.month.to_numpy(np.int32),
        "ymd": (m5["time"].dt.year * 10000 + m5["time"].dt.month * 100 + m5["time"].dt.day).to_numpy(np.int32),
    }


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def rolling_mean_std(x: np.ndarray, win: int) -> tuple[np.ndarray, np.ndarray]:
    n = len(x)
    mean = np.full(n, np.nan, np.float64)
    std = np.full(n, np.nan, np.float64)
    if win < 2 or n < win:
        return mean, std
    c1 = np.cumsum(x, dtype=np.float64)
    c2 = np.cumsum(x * x, dtype=np.float64)
    s1 = c1[win - 1 :] - np.concatenate(([0.0], c1[: n - win]))
    s2 = c2[win - 1 :] - np.concatenate(([0.0], c2[: n - win]))
    m = s1 / win
    var = (s2 - s1 * s1 / win) / (win - 1)  # sample variance, MT5-like
    var = np.maximum(var, 0.0)
    mean[win - 1 :] = m
    std[win - 1 :] = np.sqrt(var)
    return mean, std


def ema(x: np.ndarray, span: int) -> np.ndarray:
    out = np.empty_like(x, dtype=np.float64)
    if len(x) == 0:
        return out
    a = 2.0 / (span + 1.0)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1.0 - a) * out[i - 1]
    return out


def wilder_smooth(x: np.ndarray, period: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan, np.float64)
    if n < period:
        return out
    acc = np.sum(x[:period])
    out[period - 1] = acc / period
    for i in range(period, n):
        acc = acc - acc / period + x[i]
        out[i] = acc / period
    return out


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    n = len(close)
    tr = np.empty(n, np.float64)
    tr[0] = high[0] - low[0]
    pc = close[:-1]
    h = high[1:]
    l = low[1:]
    tr[1:] = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return tr


def atr_wilder(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    return wilder_smooth(true_range(high, low, close), period)


def adx_wilder(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    adx = np.full(n, np.nan, np.float64)
    if n < period * 2:
        return adx
    up = high[1:] - high[:-1]
    dn = low[:-1] - low[1:]
    plus_dm = np.zeros(n, np.float64)
    minus_dm = np.zeros(n, np.float64)
    plus_dm[1:] = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm[1:] = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = true_range(high, low, close)
    atr = wilder_smooth(tr, period)
    sm_plus = wilder_smooth(plus_dm, period)
    sm_minus = wilder_smooth(minus_dm, period)
    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    valid = (atr > 0) & np.isfinite(atr) & np.isfinite(sm_plus)
    plus_di[valid] = 100.0 * sm_plus[valid] / atr[valid]
    minus_di[valid] = 100.0 * sm_minus[valid] / atr[valid]
    di_sum = plus_di + minus_di
    dx = np.full(n, np.nan)
    ok = di_sum > 0
    dx[ok] = 100.0 * np.abs(plus_di[ok] - minus_di[ok]) / di_sum[ok]
    # Wilder of DX starting at first finite window
    first = period * 2 - 2
    if first >= n or not np.isfinite(dx[period - 1 : first + 1]).all():
        # fallback: skip nan
        finite = np.where(np.isfinite(dx))[0]
        if len(finite) < period:
            return adx
        start = finite[period - 1]
        acc = np.nansum(dx[start - period + 1 : start + 1])
        adx[start] = acc / period
        for i in range(start + 1, n):
            if not np.isfinite(dx[i]) or not np.isfinite(adx[i - 1]):
                adx[i] = adx[i - 1]
            else:
                adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
        return adx
    acc = np.sum(dx[period - 1 : first + 1])
    adx[first] = acc / period
    for i in range(first + 1, n):
        if np.isfinite(dx[i]):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
        else:
            adx[i] = adx[i - 1]
    return adx


def efficiency_ratio(close: np.ndarray, period: int = 20) -> np.ndarray:
    n = len(close)
    er = np.full(n, np.nan, np.float64)
    if n <= period:
        return er
    direction = np.abs(close[period:] - close[:-period])
    d = np.abs(np.diff(close))
    c = np.cumsum(d)
    # sum of |diff| over `period` steps ending at i: c[i-1] - c[i-1-period]
    volatility = c[period - 1 :] - np.concatenate(([0.0], c[: n - period - 1]))
    # volatility length matches close[period:]
    with np.errstate(divide="ignore", invalid="ignore"):
        er[period:] = np.where(volatility > 0, direction / volatility, 0.0)
    return er


def percentile_rank_rolling(x: np.ndarray, win: int) -> np.ndarray:
    """Approximate rolling percentile rank of x[i] within last win values."""
    n = len(x)
    out = np.full(n, np.nan, np.float64)
    if n < win:
        return out
    # stride trick is memory heavy; use a light loop (n~700k, win=200 → OK)
    for i in range(win - 1, n):
        w = x[i - win + 1 : i + 1]
        xi = x[i]
        if not np.isfinite(xi):
            continue
        finite = w[np.isfinite(w)]
        if finite.size == 0:
            continue
        out[i] = 100.0 * np.mean(finite <= xi)
    return out


def resample_h1_features(m5: pd.DataFrame) -> pd.DataFrame:
    g = m5.set_index("time").resample("1h", label="left", closed="left")
    h1 = g.agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    h1 = h1.reset_index()
    h = h1["high"].to_numpy(np.float64)
    l = h1["low"].to_numpy(np.float64)
    c = h1["close"].to_numpy(np.float64)
    h1["atr14"] = atr_wilder(h, l, c, 14)
    h1["adx14"] = adx_wilder(h, l, c, 14)
    h1["ema20"] = ema(c, 20)
    # slope over 4 H1 bars, ATR-normalized
    ema20 = h1["ema20"].to_numpy(np.float64)
    slope = np.full(len(h1), np.nan)
    slope[4:] = ema20[4:] - ema20[:-4]
    atr = h1["atr14"].to_numpy(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        h1["slope_norm"] = np.where(atr > 0, slope / atr, np.nan)
    # shift by 1 so M5 bars inside the current H1 only see the last *completed* H1
    h1["adx_closed"] = h1["adx14"].shift(1)
    h1["slope_closed"] = h1["slope_norm"].shift(1)
    h1["atr_closed"] = h1["atr14"].shift(1)
    return h1


def attach_h1_to_m5(m5: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    m5 = m5.copy()
    m5["h1_bucket"] = m5["time"].dt.floor("h")
    merged = m5.merge(
        h1[["time", "adx_closed", "slope_closed", "atr_closed"]].rename(columns={"time": "h1_bucket"}),
        on="h1_bucket",
        how="left",
    )
    return merged


def build_price_series(close: np.ndarray, high: np.ndarray, low: np.ndarray, mode: str) -> np.ndarray:
    typical = (high + low + close) / 3.0
    if mode == "close":
        return close
    if mode == "typical":
        return typical
    if mode == "residual":
        return close - ema(close, 50)
    if mode == "returns":
        r = np.empty_like(close)
        r[0] = 0.0
        r[1:] = np.diff(close)
        return r
    raise ValueError(mode)


def zscore(price: np.ndarray, lookback: int) -> np.ndarray:
    mean, std = rolling_mean_std(price, lookback)
    z = np.full(len(price), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (price - mean) / std
        z[~np.isfinite(z)] = np.nan
    return z


def atr_norm_dev(close: np.ndarray, high: np.ndarray, low: np.ndarray, lookback: int) -> np.ndarray:
    mean, _ = rolling_mean_std(close, lookback)
    atr = atr_wilder(high, low, close, 14)
    out = np.full(len(close), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (close - mean) / atr
        out[~np.isfinite(out)] = np.nan
    return out


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

# Exit codes: 1=SL, 2=TP, 3=time, 4=z-exit
# Side: +1 long, -1 short

@njit(cache=True)
def simulate(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    z: np.ndarray,
    atr: np.ndarray,
    allowed: np.ndarray,
    z_entry: float,
    confirm: int,
    persist_n: int,
    sl_pips: float,
    atr_mult: float,
    tp_rr: float,
    max_hold: int,
    cooldown: int,
    z_exit: float,
    cost_pips: float,
    pip: float,
    min_sl_pips: float,
    max_spread_to_sl: float,
):
    n = len(close)
    max_tr = n // 2 + 1
    entry_i = np.empty(max_tr, np.int64)
    exit_i = np.empty(max_tr, np.int64)
    side_a = np.empty(max_tr, np.int8)
    r_a = np.empty(max_tr, np.float64)
    slp_a = np.empty(max_tr, np.float64)
    reason_a = np.empty(max_tr, np.int8)
    hold_a = np.empty(max_tr, np.int32)

    tcount = 0
    in_pos = 0
    side = 0
    entry_px = 0.0
    sl = 0.0
    tp = 0.0
    sl_dist = 0.0
    entry_bar = 0
    next_allowed = 0
    persist_long = 0
    persist_short = 0

    for i in range(n - 1):
        zi = z[i]
        if in_pos == 1:
            # manage on bar i (this bar's range is known because we only enter
            # on a previous signal; first managed bar is the entry bar itself)
            hit_sl = False
            hit_tp = False
            if side == 1:
                if low[i] <= sl:
                    hit_sl = True
                if high[i] >= tp:
                    hit_tp = True
            else:
                if high[i] >= sl:
                    hit_sl = True
                if low[i] <= tp:
                    hit_tp = True

            exit_px = 0.0
            reason = 0
            # Conservative: if both in range, SL first. Gaps fill at open if worse.
            if hit_sl and hit_tp:
                reason = 1
                if side == 1:
                    exit_px = sl if open_[i] >= sl else open_[i]
                else:
                    exit_px = sl if open_[i] <= sl else open_[i]
            elif hit_sl:
                reason = 1
                if side == 1:
                    exit_px = sl if open_[i] >= sl else open_[i]
                else:
                    exit_px = sl if open_[i] <= sl else open_[i]
            elif hit_tp:
                reason = 2
                exit_px = tp
            else:
                held = i - entry_bar + 1
                if z_exit > 0.0 and np.isfinite(zi) and abs(zi) <= z_exit:
                    reason = 4
                    exit_px = close[i]
                elif held >= max_hold:
                    reason = 3
                    exit_px = close[i]

            if reason != 0:
                r = side * (exit_px - entry_px) / sl_dist
                r -= cost_pips * pip / sl_dist
                entry_i[tcount] = entry_bar
                exit_i[tcount] = i
                side_a[tcount] = side
                r_a[tcount] = r
                slp_a[tcount] = sl_dist / pip
                reason_a[tcount] = reason
                hold_a[tcount] = i - entry_bar + 1
                tcount += 1
                in_pos = 0
                next_allowed = i + 1 + cooldown
            continue

        # flatten persist counters when not in a trade
        if not np.isfinite(zi):
            persist_long = 0
            persist_short = 0
            continue
        if zi <= -z_entry:
            persist_long += 1
            persist_short = 0
        elif zi >= z_entry:
            persist_short += 1
            persist_long = 0
        else:
            persist_long = 0
            persist_short = 0

        if i < next_allowed:
            continue
        if not allowed[i]:
            continue

        sig = 0
        if confirm == 0:
            if zi <= -z_entry:
                sig = 1
            elif zi >= z_entry:
                sig = -1
        elif confirm == 1:
            # one-bar reversal: previous extreme, current retrace toward 0
            if i == 0 or not np.isfinite(z[i - 1]):
                sig = 0
            else:
                zp = z[i - 1]
                if zp <= -z_entry and zi > zp and zi < 0.0:
                    sig = 1
                elif zp >= z_entry and zi < zp and zi > 0.0:
                    sig = -1
        elif confirm == 2:
            if persist_long >= persist_n:
                sig = 1
            elif persist_short >= persist_n:
                sig = -1
        elif confirm == 3:
            # was beyond, now back inside the band (reversion started)
            if i == 0 or not np.isfinite(z[i - 1]):
                sig = 0
            else:
                zp = z[i - 1]
                if zp <= -z_entry and zi > -z_entry and zi < 0.0:
                    sig = 1
                elif zp >= z_entry and zi < z_entry and zi > 0.0:
                    sig = -1

        if sig == 0:
            continue

        # SL distance from completed bar i; fill at next open
        if atr_mult > 0.0:
            if not np.isfinite(atr[i]) or atr[i] <= 0.0:
                continue
            sl_dist = atr[i] * atr_mult
        else:
            sl_dist = sl_pips * pip
        sl_p = sl_dist / pip
        if sl_p < min_sl_pips:
            continue
        if sl_p > 0.0 and (cost_pips / sl_p) > max_spread_to_sl:
            continue

        fill_i = i + 1
        entry_px = open_[fill_i]
        if not np.isfinite(entry_px) or entry_px <= 0.0:
            continue
        side = sig
        if side == 1:
            sl = entry_px - sl_dist
            tp = entry_px + tp_rr * sl_dist
        else:
            sl = entry_px + sl_dist
            tp = entry_px - tp_rr * sl_dist
        entry_bar = fill_i
        in_pos = 1

    return (
        entry_i[:tcount].copy(),
        exit_i[:tcount].copy(),
        side_a[:tcount].copy(),
        r_a[:tcount].copy(),
        slp_a[:tcount].copy(),
        reason_a[:tcount].copy(),
        hold_a[:tcount].copy(),
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class Metrics:
    n: int
    win_rate: float
    expectancy: float
    avg_win: float
    avg_loss: float
    payoff: float
    profit_factor: float
    sum_r: float
    max_dd_r: float
    max_dd_pct: float
    end_eq: float
    time_stop_share: float
    sl_share: float
    tp_share: float
    z_exit_share: float
    avg_hold: float
    avg_sl_pips: float
    median_r: float
    p05_r: float
    p95_r: float


def empty_metrics() -> Metrics:
    return Metrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def metrics_from_trades(r: np.ndarray, reason: np.ndarray | None = None, hold: np.ndarray | None = None, slp: np.ndarray | None = None, risk: float = 0.01) -> Metrics:
    if r is None or len(r) == 0:
        return empty_metrics()
    n = int(len(r))
    wins = r[r > 0]
    losses = r[r <= 0]
    wr = float(len(wins) / n)
    exp = float(np.mean(r))
    avg_w = float(np.mean(wins)) if len(wins) else 0.0
    avg_l = float(np.mean(losses)) if len(losses) else 0.0
    payoff = float(avg_w / abs(avg_l)) if avg_l != 0 else 0.0
    gp = float(np.sum(wins)) if len(wins) else 0.0
    gl = float(-np.sum(losses)) if len(losses) else 0.0
    pf = float(gp / gl) if gl > 0 else (99.0 if gp > 0 else 0.0)
    eq_r = np.cumsum(r)
    peak = np.maximum.accumulate(eq_r)
    dd = peak - eq_r
    max_dd_r = float(np.max(dd)) if len(dd) else 0.0
    # compounding 1% of equity
    eq = np.empty(n + 1, np.float64)
    eq[0] = 1.0
    for i in range(n):
        eq[i + 1] = eq[i] * (1.0 + risk * r[i])
    peak_e = np.maximum.accumulate(eq)
    dd_pct = (peak_e - eq) / peak_e
    max_dd_pct = float(np.max(dd_pct) * 100.0)
    shares = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    if reason is not None and len(reason):
        for k in shares:
            shares[k] = float(np.mean(reason == k))
    return Metrics(
        n=n,
        win_rate=wr,
        expectancy=exp,
        avg_win=avg_w,
        avg_loss=avg_l,
        payoff=payoff,
        profit_factor=pf,
        sum_r=float(np.sum(r)),
        max_dd_r=max_dd_r,
        max_dd_pct=max_dd_pct,
        end_eq=float(eq[-1]),
        time_stop_share=shares[3],
        sl_share=shares[1],
        tp_share=shares[2],
        z_exit_share=shares[4],
        avg_hold=float(np.mean(hold)) if hold is not None and len(hold) else 0.0,
        avg_sl_pips=float(np.mean(slp)) if slp is not None and len(slp) else 0.0,
        median_r=float(np.median(r)),
        p05_r=float(np.percentile(r, 5)),
        p95_r=float(np.percentile(r, 95)),
    )


def metrics_to_dict(m: Metrics) -> dict:
    return {
        "trades": m.n,
        "win_rate": round(m.win_rate, 4),
        "expectancy_r": round(m.expectancy, 4),
        "avg_win_r": round(m.avg_win, 4),
        "avg_loss_r": round(m.avg_loss, 4),
        "payoff": round(m.payoff, 4),
        "profit_factor": round(m.profit_factor, 4),
        "sum_r": round(m.sum_r, 2),
        "max_dd_r": round(m.max_dd_r, 2),
        "max_dd_pct_1pct_risk": round(m.max_dd_pct, 2),
        "end_equity_multiple": round(m.end_eq, 4),
        "time_stop_share": round(m.time_stop_share, 4),
        "sl_share": round(m.sl_share, 4),
        "tp_share": round(m.tp_share, 4),
        "z_exit_share": round(m.z_exit_share, 4),
        "avg_hold_bars": round(m.avg_hold, 2),
        "avg_sl_pips": round(m.avg_sl_pips, 2),
        "median_r": round(m.median_r, 4),
        "p05_r": round(m.p05_r, 4),
        "p95_r": round(m.p95_r, 4),
    }


def yearly_breakdown(r: np.ndarray, exit_i: np.ndarray, years: np.ndarray) -> list[dict]:
    if len(r) == 0:
        return []
    y = years[exit_i]
    out = []
    for yr in sorted(set(int(v) for v in y)):
        mask = y == yr
        m = metrics_from_trades(r[mask])
        d = metrics_to_dict(m)
        d["year"] = int(yr)
        out.append(d)
    return out


def mask_period(entry_i: np.ndarray, times: np.ndarray, start: np.datetime64, end: np.datetime64) -> np.ndarray:
    if len(entry_i) == 0:
        return np.zeros(0, dtype=bool)
    t = times[entry_i]
    return (t >= start) & (t < end)


def session_mask_array(hour: np.ndarray, minute: np.ndarray, dow: np.ndarray, mode: str) -> np.ndarray:
    """Session windows on HistData Eastern wall clock.

    Asian 19:00-04:00, London 03:00-12:00, NY 08:00-17:00, overlap 08:00-12:00.
    Always blocks broker rollover 16:45-17:15 and Friday after 16:00.
    """
    n = len(hour)
    rollover = ((hour == 16) & (minute >= 45)) | ((hour == 17) & (minute < 15))
    friday_late = (dow == 4) & (hour >= 16)
    blocked = rollover | friday_late
    asian = (hour >= 19) | (hour < 4)
    london = (hour >= 3) & (hour < 12)
    ny = (hour >= 8) & (hour < 17)
    overlap = (hour >= 8) & (hour < 12)
    if mode == "all":
        allow = np.ones(n, dtype=np.bool_)
    elif mode == "london":
        allow = london
    elif mode == "ny":
        allow = ny
    elif mode == "overlap":
        allow = overlap
    elif mode == "asian":
        allow = asian
    elif mode == "london_ny":
        allow = london | ny
    else:
        allow = np.ones(n, dtype=np.bool_)
    return allow & ~blocked


def monte_carlo(r: np.ndarray, n_paths: int = 1000, risk: float = 0.01, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    n = len(r)
    if n < 20:
        return {"paths": 0, "note": "insufficient trades"}
    end_eq = np.empty(n_paths, np.float64)
    max_dd = np.empty(n_paths, np.float64)
    min_eq = np.empty(n_paths, np.float64)
    longest_loss = np.empty(n_paths, np.int32)
    breach_20 = 0
    breach_30 = 0
    breach_50 = 0
    for p in range(n_paths):
        sample = rng.choice(r, size=n, replace=True)
        eq = 1.0
        peak = 1.0
        ddmax = 0.0
        eqmin = 1.0
        streak = 0
        maxstreak = 0
        for x in sample:
            eq *= 1.0 + risk * x
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > ddmax:
                ddmax = dd
            if eq < eqmin:
                eqmin = eq
            if x <= 0:
                streak += 1
                if streak > maxstreak:
                    maxstreak = streak
            else:
                streak = 0
        end_eq[p] = eq
        max_dd[p] = ddmax * 100.0
        min_eq[p] = eqmin
        longest_loss[p] = maxstreak
        if ddmax >= 0.20:
            breach_20 += 1
        if ddmax >= 0.30:
            breach_30 += 1
        if eqmin < 0.50:
            breach_50 += 1
    return {
        "paths": n_paths,
        "risk_pct": risk * 100.0,
        "median_end_equity": round(float(np.median(end_eq)), 4),
        "p05_end_equity": round(float(np.percentile(end_eq, 5)), 4),
        "p10_end_equity": round(float(np.percentile(end_eq, 10)), 4),
        "p90_end_equity": round(float(np.percentile(end_eq, 90)), 4),
        "median_max_dd_pct": round(float(np.median(max_dd)), 2),
        "p90_max_dd_pct": round(float(np.percentile(max_dd, 90)), 2),
        "p95_max_dd_pct": round(float(np.percentile(max_dd, 95)), 2),
        "median_longest_loss_streak": int(np.median(longest_loss)),
        "p95_longest_loss_streak": int(np.percentile(longest_loss, 95)),
        "prob_dd_ge_20pct": round(breach_20 / n_paths, 4),
        "prob_dd_ge_30pct": round(breach_30 / n_paths, 4),
        "prob_equity_below_50pct": round(breach_50 / n_paths, 4),
        "median_min_equity": round(float(np.median(min_eq)), 4),
    }


def downsample_equity(r: np.ndarray, entry_i: np.ndarray, times: np.ndarray, start_eq: float = 10000.0, risk: float = 0.01, every: int = 1) -> list[dict]:
    if len(r) == 0:
        return []
    eq = start_eq
    peak = start_eq
    points = []
    for k in range(len(r)):
        eq *= 1.0 + risk * r[k]
        if eq > peak:
            peak = eq
        if k % every == 0 or k == len(r) - 1:
            t = pd.Timestamp(times[entry_i[k]]).strftime("%Y-%m-%d")
            points.append({"t": t, "equity": round(eq, 2), "dd_pct": round((peak - eq) / peak * 100.0, 2), "i": int(k)})
    # weekly-ish: if too many, thin
    if len(points) > 400:
        step = int(np.ceil(len(points) / 360))
        tail = points[-1]
        points = points[::step]
        if points[-1] is not tail:
            points.append(tail)
    return points
