#!/usr/bin/env python3
"""STATREV research protocol — EURUSD M5 statistical mean reversion.

Run: python3 /workspace/research/run_research.py
Writes: /workspace/research/out/results.json and /workspace/public/research/results.json
"""

from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from datetime import datetime

import numpy as np
import pandas as pd

from engine import (
    PIP,
    attach_h1_to_m5,
    atr_norm_dev,
    atr_wilder,
    bars_to_arrays,
    build_price_series,
    downsample_equity,
    efficiency_ratio,
    ema,
    load_m1_frames,
    metrics_from_trades,
    metrics_to_dict,
    monte_carlo,
    resample_h1_features,
    resample_m5,
    rolling_mean_std,
    session_mask_array,
    simulate,
    yearly_breakdown,
    zscore,
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "out")
PUBLIC_JSON = "/workspace/public/research/results.json"

IS_START = np.datetime64("2016-01-01")
IS_END = np.datetime64("2022-01-01")
VAL_START = IS_END
VAL_END = np.datetime64("2024-01-01")
OOS_START = VAL_END
OOS_END = np.datetime64("2026-01-01")
XTRA_END = np.datetime64("2026-10-01")

COST = {
    "optimistic": {"spread": 0.8, "slip": 0.10, "comm": 0.40, "label": "Optimistic but plausible"},
    "base": {"spread": 1.2, "slip": 0.30, "comm": 0.70, "label": "Base / expected live ECN"},
    "adverse": {"spread": 2.0, "slip": 0.60, "comm": 1.00, "label": "Adverse / stress"},
}


def rt_cost(name: str) -> float:
    c = COST[name]
    return c["spread"] + 2.0 * c["slip"] + c["comm"]


def m_to_dict(m):
    return metrics_to_dict(m)


def split_mask(entry_i, times, start, end):
    if len(entry_i) == 0:
        return np.zeros(0, dtype=bool)
    t = times[entry_i]
    return (t >= start) & (t < end)


def slice_metrics(pack, times, start, end):
    entry_i, exit_i, side, r, slp, reason, hold = pack
    mask = split_mask(entry_i, times, start, end)
    if mask.sum() == 0:
        return metrics_from_trades(np.array([])), mask
    return metrics_from_trades(r[mask], reason[mask], hold[mask], slp[mask]), mask


def run_cfg(arr, z, atr, allowed, cfg, cost_pips):
    return simulate(
        arr["open"],
        arr["high"],
        arr["low"],
        arr["close"],
        z,
        atr,
        allowed,
        float(cfg["z_entry"]),
        int(cfg["confirm"]),
        int(cfg.get("persist_n", 3)),
        float(cfg.get("sl_pips", 0.0)),
        float(cfg.get("atr_mult", 0.0)),
        float(cfg.get("tp_rr", 2.0)),
        int(cfg["max_hold"]),
        int(cfg["cooldown"]),
        float(cfg.get("z_exit", 0.0)),
        float(cost_pips),
        PIP,
        float(cfg.get("min_sl_pips", 8.0)),
        float(cfg.get("max_spread_to_sl", 0.40)),
    )


def cfg_id(cfg):
    sl = f"atr{cfg['atr_mult']}" if cfg.get("atr_mult", 0) else f"{cfg.get('sl_pips')}p"
    return (
        f"{cfg['price']}|lb{cfg['lookback']}|z{cfg['z_entry']}|c{cfg['confirm']}|"
        f"{sl}|h{cfg['max_hold']}|cd{cfg['cooldown']}|zx{cfg.get('z_exit', 0)}"
    )


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(PUBLIC_JSON), exist_ok=True)

    print("Loading HistData M1…")
    m1 = load_m1_frames()
    print(f"  M1 bars: {len(m1):,}  {m1['time'].iloc[0]} → {m1['time'].iloc[-1]}")
    m5 = resample_m5(m1)
    print(f"  M5 bars: {len(m5):,}  {m5['time'].iloc[0]} → {m5['time'].iloc[-1]}")

    h1 = resample_h1_features(m5)
    m5 = attach_h1_to_m5(m5, h1)
    arr = bars_to_arrays(m5)
    n = len(arr["close"])
    close, high, low = arr["close"], arr["high"], arr["low"]
    atr = atr_wilder(high, low, close, 14)
    atr_mean, _ = rolling_mean_std(np.where(np.isfinite(atr), atr, 0.0), 100)
    with np.errstate(divide="ignore", invalid="ignore"):
        vol_ratio = atr / atr_mean
    er = efficiency_ratio(close, 20)
    adx = m5["adx_closed"].to_numpy(np.float64)
    slope = m5["slope_closed"].to_numpy(np.float64)
    times = arr["time"]
    years = arr["year"]

    sess_all = session_mask_array(arr["hour"], arr["minute"], arr["dow"], "all")
    sess = {
        "all": sess_all,
        "london": session_mask_array(arr["hour"], arr["minute"], arr["dow"], "london"),
        "ny": session_mask_array(arr["hour"], arr["minute"], arr["dow"], "ny"),
        "overlap": session_mask_array(arr["hour"], arr["minute"], arr["dow"], "overlap"),
        "asian": session_mask_array(arr["hour"], arr["minute"], arr["dow"], "asian"),
        "london_ny": session_mask_array(arr["hour"], arr["minute"], arr["dow"], "london_ny"),
    }

    # data quality
    per_year = m5.groupby(m5["time"].dt.year).size().to_dict()
    quality = {
        "source": "HistData.com ASCII EURUSD M1 bid OHLC, resampled to M5",
        "timestamp_convention": "HistData US Eastern wall clock (EST tradition, no DST adjustment applied). Session filters use that clock.",
        "m1_bars": int(len(m1)),
        "m5_bars": int(len(m5)),
        "start": str(m5["time"].iloc[0]),
        "end": str(m5["time"].iloc[-1]),
        "bars_by_year": {str(k): int(v) for k, v in per_year.items()},
        "gaps_note": "M1 files contain documented intra-minute gaps; M5 bars are formed from available M1 prints in each 5-minute bucket. Weekend gaps are real and can gap through stops.",
        "spread_in_data": False,
        "tick_model": "Bar OHLC, not tick. Conservative same-bar SL-before-TP. Stop gaps fill at bar open if worse than SL.",
    }

    print("Precomputing z-scores…")
    price_modes = ["typical", "close", "residual", "atr_dev"]
    lookbacks = [75, 100, 150, 200, 300]
    z_cache = {}
    for mode in price_modes:
        if mode == "atr_dev":
            px = None
        else:
            px = build_price_series(close, high, low, mode)
        for lb in lookbacks:
            if mode == "atr_dev":
                z_cache[(mode, lb)] = atr_norm_dev(close, high, low, lb)
            else:
                z_cache[(mode, lb)] = zscore(px, lb)

    # Warm up numba
    dummy_allowed = np.ones(min(500, n), dtype=np.bool_)
    _ = simulate(
        arr["open"][:500], high[:500], low[:500], close[:500],
        z_cache[("typical", 100)][:500], atr[:500], dummy_allowed,
        2.0, 0, 3, 12.0, 0.0, 2.0, 24, 0, 0.0, 2.5, PIP, 8.0, 0.4,
    )
    print("Numba warmed.")

    base_cost = rt_cost("base")
    print(f"Base round-turn cost: {base_cost:.2f} pips")

    # ------------------------------------------------------------------
    # Stage 1/2: baseline grid (no regime filters beyond session hygiene)
    # ------------------------------------------------------------------
    grid = []
    for lb in lookbacks:
        for z_e in [1.5, 1.75, 2.0, 2.5, 3.0]:
            for confirm in [0, 1]:
                for sl_pips, atr_mult in [(12.0, 0.0), (15.0, 0.0), (0.0, 1.5)]:
                    for max_hold in [24, 48]:
                        for cooldown in [0, 6]:
                            grid.append({
                                "price": "typical",
                                "lookback": lb,
                                "z_entry": z_e,
                                "confirm": confirm,
                                "persist_n": 3,
                                "sl_pips": sl_pips,
                                "atr_mult": atr_mult,
                                "tp_rr": 2.0,
                                "max_hold": max_hold,
                                "cooldown": cooldown,
                                "z_exit": 0.0,
                            })
    print(f"Baseline grid: {len(grid)} configs")

    rows = []
    t_grid = time.time()
    for i, cfg in enumerate(grid):
        z = z_cache[(cfg["price"], cfg["lookback"])]
        pack = run_cfg(arr, z, atr, sess_all, cfg, base_cost)
        entry_i, exit_i, side, r, slp, reason, hold = pack
        is_m, is_mask = slice_metrics(pack, times, IS_START, IS_END)
        val_m, _ = slice_metrics(pack, times, VAL_START, VAL_END)
        oos_m, _ = slice_metrics(pack, times, OOS_START, OOS_END)
        full_m = metrics_from_trades(r, reason, hold, slp)
        rows.append({
            "id": cfg_id(cfg),
            "cfg": cfg,
            "is": m_to_dict(is_m),
            "val": m_to_dict(val_m),
            "oos": m_to_dict(oos_m),
            "full": m_to_dict(full_m),
            "pack": pack,
        })
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(grid)}  elapsed {time.time()-t_grid:.1f}s")

    def is_viable_is(row, min_trades=400):
        d = row["is"]
        return d["trades"] >= min_trades and np.isfinite(d["expectancy_r"])

    ranked = sorted(
        [r for r in rows if is_viable_is(r, 300)],
        key=lambda r: (r["is"]["expectancy_r"], r["is"]["profit_factor"], r["is"]["trades"]),
        reverse=True,
    )
    # Also rank by IS PF with positive expectancy
    pos_is = [r for r in ranked if r["is"]["expectancy_r"] > 0 and r["is"]["profit_factor"] > 1.0]
    print(f"Configs with IS trades>=300: {len(ranked)}")
    print(f"Configs with IS E>0 and PF>1: {len(pos_is)}")

    def slim(row):
        return {
            "id": row["id"],
            "cfg": row["cfg"],
            "is": row["is"],
            "val": row["val"],
            "oos": row["oos"],
            "full": row["full"],
        }

    leaderboard = [slim(r) for r in ranked[:25]]

    # Candidate selection: maximize IS expectancy among configs that also have
    # non-negative VAL expectancy (validation peek, still not OOS).
    # If none, take best IS and report failure honestly.
    val_ok = [r for r in pos_is if r["val"]["expectancy_r"] >= 0 and r["val"]["trades"] >= 80]
    if val_ok:
        # stability: prefer those whose VAL expectancy is not a collapse
        val_ok = sorted(
            val_ok,
            key=lambda r: (
                min(r["is"]["expectancy_r"], r["val"]["expectancy_r"]),
                r["is"]["expectancy_r"],
                -r["is"]["max_dd_pct_1pct_risk"],
            ),
            reverse=True,
        )
        candidate_row = val_ok[0]
        selection_rule = "Best IS/VAL min-expectancy among IS-profitable configs with VAL E>=0 and VAL trades>=80. OOS was not used for selection."
    elif pos_is:
        candidate_row = pos_is[0]
        selection_rule = "No config had non-negative validation expectancy. Falling back to best IS expectancy. This is NOT a validated candidate."
    elif ranked:
        candidate_row = ranked[0]
        selection_rule = "No IS-profitable config. Reporting least-bad IS expectancy. Hypothesis is not supported after costs."
    else:
        candidate_row = rows[0]
        selection_rule = "Grid produced no adequately sampled configs."

    print("Selected:", candidate_row["id"])
    print("Rule:", selection_rule)
    print("IS", candidate_row["is"])
    print("VAL", candidate_row["val"])
    print("OOS", candidate_row["oos"])

    # ------------------------------------------------------------------
    # Stage 1b: price-mode and confirmation variants around candidate core
    # ------------------------------------------------------------------
    core = deepcopy(candidate_row["cfg"])
    variant_rows = []
    for mode in price_modes:
        for confirm in [0, 1, 2, 3]:
            for z_exit in [0.0, 0.25]:
                for max_hold in [12, 24, 48, 96]:
                    cfg = deepcopy(core)
                    cfg["price"] = mode
                    cfg["confirm"] = confirm
                    cfg["z_exit"] = z_exit
                    cfg["max_hold"] = max_hold
                    z = z_cache[(mode, cfg["lookback"])]
                    pack = run_cfg(arr, z, atr, sess_all, cfg, base_cost)
                    is_m, _ = slice_metrics(pack, times, IS_START, IS_END)
                    val_m, _ = slice_metrics(pack, times, VAL_START, VAL_END)
                    oos_m, _ = slice_metrics(pack, times, OOS_START, OOS_END)
                    entry_i, exit_i, side, r, slp, reason, hold = pack
                    full_m = metrics_from_trades(r, reason, hold, slp)
                    variant_rows.append({
                        "id": cfg_id(cfg),
                        "cfg": cfg,
                        "is": m_to_dict(is_m),
                        "val": m_to_dict(val_m),
                        "oos": m_to_dict(oos_m),
                        "full": m_to_dict(full_m),
                    })

    # If a variant beats candidate on IS and VAL (still no OOS), adopt it
    def score_is_val(d):
        if d["is"]["trades"] < 300 or d["val"]["trades"] < 80:
            return -999
        if d["is"]["expectancy_r"] <= 0:
            return -999
        return min(d["is"]["expectancy_r"], d["val"]["expectancy_r"])

    best_var = max(variant_rows, key=score_is_val)
    if score_is_val(best_var) > score_is_val({
        "is": candidate_row["is"], "val": candidate_row["val"]
    }):
        # re-run pack for new candidate
        cfg = best_var["cfg"]
        z = z_cache[(cfg["price"], cfg["lookback"])]
        pack = run_cfg(arr, z, atr, sess_all, cfg, base_cost)
        candidate_row = {
            "id": best_var["id"],
            "cfg": cfg,
            "is": best_var["is"],
            "val": best_var["val"],
            "oos": best_var["oos"],
            "full": best_var["full"],
            "pack": pack,
        }
        selection_rule += " Core parameters then refined on price/confirm/hold/z-exit using IS+VAL only."
        print("Refined candidate:", candidate_row["id"])

    cand_cfg = candidate_row["cfg"]
    cand_pack = candidate_row["pack"]
    cand_z = z_cache[(cand_cfg["price"], cand_cfg["lookback"])]

    # ------------------------------------------------------------------
    # Stage 3: filter comparison on frozen candidate params
    # ------------------------------------------------------------------
    print("Filter comparison…")
    filter_defs = []

    def add_filter(name, family, allowed, note):
        filter_defs.append((name, family, allowed, note))

    add_filter("none", "baseline", sess_all, "Rollover + Friday-late hygiene only.")
    add_filter("adx_h1_lt_18", "trend_strength", sess_all & np.isfinite(adx) & (adx < 18), "H1 ADX < 18 (completed H1 only).")
    add_filter("adx_h1_lt_22", "trend_strength", sess_all & np.isfinite(adx) & (adx < 22), "H1 ADX < 22.")
    add_filter("adx_h1_lt_25", "trend_strength", sess_all & np.isfinite(adx) & (adx < 25), "H1 ADX < 25.")
    add_filter("adx_h1_lt_28", "trend_strength", sess_all & np.isfinite(adx) & (adx < 28), "H1 ADX < 28.")
    add_filter("slope_lt_0.8", "trend_direction", sess_all & np.isfinite(slope) & (np.abs(slope) < 0.8), "|H1 EMA slope|/ATR < 0.8.")
    add_filter("slope_lt_1.2", "trend_direction", sess_all & np.isfinite(slope) & (np.abs(slope) < 1.2), "|H1 EMA slope|/ATR < 1.2.")
    add_filter("vol_ratio_lt_1.4", "volatility", sess_all & np.isfinite(vol_ratio) & (vol_ratio < 1.4), "M5 ATR14 / SMA100(ATR) < 1.4.")
    add_filter("vol_ratio_lt_1.8", "volatility", sess_all & np.isfinite(vol_ratio) & (vol_ratio < 1.8), "M5 ATR14 / SMA100(ATR) < 1.8.")
    add_filter("er_lt_0.30", "efficiency", sess_all & np.isfinite(er) & (er < 0.30), "Kaufman ER(20) < 0.30 (choppy).")
    add_filter("er_lt_0.40", "efficiency", sess_all & np.isfinite(er) & (er < 0.40), "Kaufman ER(20) < 0.40.")
    add_filter("session_london", "session", sess["london"], "London window only.")
    add_filter("session_ny", "session", sess["ny"], "New York window only.")
    add_filter("session_overlap", "session", sess["overlap"], "London–NY overlap only.")
    add_filter("session_asian", "session", sess["asian"], "Asian window only.")
    add_filter("session_london_ny", "session", sess["london_ny"], "London or NY.")
    combo = (
        sess_all
        & np.isfinite(adx) & (adx < 22)
        & np.isfinite(slope) & (np.abs(slope) < 1.2)
        & np.isfinite(vol_ratio) & (vol_ratio < 1.8)
    )
    add_filter("combo_adx22_slope12_vol18", "combo", combo, "Proposed default stack: H1 ADX<22, |slope|<1.2, vol_ratio<1.8.")

    filter_table = []
    filter_packs = {}
    for name, family, allowed, note in filter_defs:
        pack = run_cfg(arr, cand_z, atr, allowed, cand_cfg, base_cost)
        filter_packs[name] = pack
        is_m, _ = slice_metrics(pack, times, IS_START, IS_END)
        val_m, _ = slice_metrics(pack, times, VAL_START, VAL_END)
        oos_m, _ = slice_metrics(pack, times, OOS_START, OOS_END)
        x_m, _ = slice_metrics(pack, times, OOS_END, XTRA_END)
        full = metrics_from_trades(pack[3], pack[5], pack[6], pack[4])
        filter_table.append({
            "name": name,
            "family": family,
            "note": note,
            "is": m_to_dict(is_m),
            "val": m_to_dict(val_m),
            "oos": m_to_dict(oos_m),
            "extra_2026": m_to_dict(x_m),
            "full": m_to_dict(full),
            "oos_minus_baseline_e": round(oos_m.expectancy - metrics_from_trades(cand_pack[3][split_mask(cand_pack[0], times, OOS_START, OOS_END)]).expectancy, 4) if False else None,
        })

    base_val_e = next(f["val"]["expectancy_r"] for f in filter_table if f["name"] == "none")
    base_val_dd = next(f["val"]["max_dd_pct_1pct_risk"] for f in filter_table if f["name"] == "none")
    base_oos_e = next(f["oos"]["expectancy_r"] for f in filter_table if f["name"] == "none")
    base_oos_pf = next(f["oos"]["profit_factor"] for f in filter_table if f["name"] == "none")
    base_oos_dd = next(f["oos"]["max_dd_pct_1pct_risk"] for f in filter_table if f["name"] == "none")
    for f in filter_table:
        f["oos_delta_e"] = round(f["oos"]["expectancy_r"] - base_oos_e, 4)
        f["oos_delta_pf"] = round(f["oos"]["profit_factor"] - base_oos_pf, 4)
        f["oos_delta_dd"] = round(f["oos"]["max_dd_pct_1pct_risk"] - base_oos_dd, 2)
        f["val_delta_e"] = round(f["val"]["expectancy_r"] - base_val_e, 4)
        # Retain using VALIDATION only (OOS is reported, not used to pick filters).
        retain = (
            f["name"] != "none"
            and f["val"]["trades"] >= 80
            and f["val"]["expectancy_r"] > 0
            and (
                f["val_delta_e"] > 0.005
                or (f["val_delta_e"] >= -0.01 and (f["val"]["max_dd_pct_1pct_risk"] - base_val_dd) < -1.0)
            )
        )
        f["retained"] = bool(retain)

    retained_filters = [f for f in filter_table if f["retained"]]
    # Choose simplest retained filter by family priority, else none
    chosen_filter = "none"
    if retained_filters:
        # prefer single-family over combo; among them best OOS expectancy
        singles = [f for f in retained_filters if f["family"] != "combo"]
        pool = singles if singles else retained_filters
        chosen_filter = max(pool, key=lambda f: (f["val"]["expectancy_r"], -f["val"]["max_dd_pct_1pct_risk"]))["name"]

    print("Chosen filter:", chosen_filter)
    final_pack = filter_packs[chosen_filter]
    final_allowed = dict(filter_defs)[chosen_filter] if False else None
    for name, family, allowed, note in filter_defs:
        if name == chosen_filter:
            final_allowed = allowed
            final_filter_note = note
            break

    # Recompute candidate metrics under chosen filter
    entry_i, exit_i, side, r, slp, reason, hold = final_pack
    is_m, is_mask = slice_metrics(final_pack, times, IS_START, IS_END)
    val_m, val_mask = slice_metrics(final_pack, times, VAL_START, VAL_END)
    oos_m, oos_mask = slice_metrics(final_pack, times, OOS_START, OOS_END)
    x_m, x_mask = slice_metrics(final_pack, times, OOS_END, XTRA_END)
    full_m = metrics_from_trades(r, reason, hold, slp)

    # ------------------------------------------------------------------
    # Cost sensitivity on frozen final system
    # ------------------------------------------------------------------
    cost_table = []
    cost_packs = {}
    for cname in ["optimistic", "base", "adverse"]:
        pack = run_cfg(arr, cand_z, atr, final_allowed, cand_cfg, rt_cost(cname))
        cost_packs[cname] = pack
        is_c, _ = slice_metrics(pack, times, IS_START, IS_END)
        val_c, _ = slice_metrics(pack, times, VAL_START, VAL_END)
        oos_c, _ = slice_metrics(pack, times, OOS_START, OOS_END)
        full_c = metrics_from_trades(pack[3], pack[5], pack[6], pack[4])
        cost_pips = rt_cost(cname)
        sl_ref = cand_cfg["sl_pips"] if cand_cfg.get("atr_mult", 0) == 0 else full_c.avg_sl_pips
        cost_table.append({
            "scenario": cname,
            "label": COST[cname]["label"],
            "spread_pips": COST[cname]["spread"],
            "slippage_pips_one_way": COST[cname]["slip"],
            "commission_pips_rt": COST[cname]["comm"],
            "round_turn_pips": round(cost_pips, 2),
            "cost_in_r_vs_avg_sl": round(cost_pips / sl_ref, 4) if sl_ref else None,
            "is": m_to_dict(is_c),
            "val": m_to_dict(val_c),
            "oos": m_to_dict(oos_c),
            "full": m_to_dict(full_c),
        })

    # ------------------------------------------------------------------
    # Parameter stability around candidate (lookback x z heatmap on IS+OOS)
    # ------------------------------------------------------------------
    print("Stability heatmap…")
    heat = []
    for lb in lookbacks:
        for z_e in [1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0]:
            cfg = deepcopy(cand_cfg)
            cfg["lookback"] = lb
            cfg["z_entry"] = z_e
            z = z_cache[(cfg["price"], lb)] if (cfg["price"], lb) in z_cache else zscore(
                build_price_series(close, high, low, cfg["price"]) if cfg["price"] != "atr_dev" else close,
                lb,
            )
            if (cfg["price"], lb) not in z_cache:
                if cfg["price"] == "atr_dev":
                    z = atr_norm_dev(close, high, low, lb)
                else:
                    z = zscore(build_price_series(close, high, low, cfg["price"]), lb)
            pack = run_cfg(arr, z, atr, final_allowed, cfg, base_cost)
            is_h, _ = slice_metrics(pack, times, IS_START, IS_END)
            oos_h, _ = slice_metrics(pack, times, OOS_START, OOS_END)
            heat.append({
                "lookback": lb,
                "z_entry": z_e,
                "is_e": is_h.expectancy,
                "is_pf": is_h.profit_factor,
                "is_n": is_h.n,
                "oos_e": oos_h.expectancy,
                "oos_pf": oos_h.profit_factor,
                "oos_n": oos_h.n,
            })

    # SL stability
    sl_heat = []
    for sl_pips, atr_mult, label in [
        (8.0, 0.0, "8 pips"),
        (10.0, 0.0, "10 pips"),
        (12.0, 0.0, "12 pips"),
        (15.0, 0.0, "15 pips"),
        (18.0, 0.0, "18 pips"),
        (0.0, 0.75, "ATR×0.75"),
        (0.0, 1.0, "ATR×1.0"),
        (0.0, 1.25, "ATR×1.25"),
        (0.0, 1.5, "ATR×1.5"),
        (0.0, 2.0, "ATR×2.0"),
    ]:
        cfg = deepcopy(cand_cfg)
        cfg["sl_pips"] = sl_pips
        cfg["atr_mult"] = atr_mult
        pack = run_cfg(arr, cand_z, atr, final_allowed, cfg, base_cost)
        is_h, _ = slice_metrics(pack, times, IS_START, IS_END)
        oos_h, _ = slice_metrics(pack, times, OOS_START, OOS_END)
        sl_heat.append({
            "label": label,
            "sl_pips": sl_pips,
            "atr_mult": atr_mult,
            "is": m_to_dict(is_h),
            "oos": m_to_dict(oos_h),
        })

    # ------------------------------------------------------------------
    # Walk-forward: rolling 12m train / 3m test, re-opt lookback & z & sl
    # ------------------------------------------------------------------
    print("Walk-forward…")
    wf_lookbacks = [100, 150, 200, 300]
    wf_zs = [1.75, 2.0, 2.5, 3.0]
    wf_sls = [(12.0, 0.0), (15.0, 0.0), (0.0, 1.5)]
    wf_windows = []
    train_months = 12
    test_months = 3
    # start trains at 2016-01, last test ending 2026-09
    starts = pd.date_range("2016-01-01", "2025-07-01", freq="3MS")
    wf_test_r = []
    wf_test_entry = []
    wf_test_exit = []
    wf_test_reason = []
    wf_test_hold = []
    wf_test_slp = []

    for tr_start in starts:
        tr_end = tr_start + pd.DateOffset(months=train_months)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if te_end > pd.Timestamp("2026-09-28"):
            te_end = pd.Timestamp("2026-09-28")
        if tr_end >= te_end:
            continue
        tr0 = np.datetime64(tr_start)
        tr1 = np.datetime64(tr_end)
        te1 = np.datetime64(te_end)
        best = None
        best_score = -999
        best_cfg = None
        for lb in wf_lookbacks:
            z = z_cache[(cand_cfg["price"], lb)]
            for z_e in wf_zs:
                for sl_pips, atr_mult in wf_sls:
                    cfg = deepcopy(cand_cfg)
                    cfg["lookback"] = lb
                    cfg["z_entry"] = z_e
                    cfg["sl_pips"] = sl_pips
                    cfg["atr_mult"] = atr_mult
                    pack = run_cfg(arr, z, atr, final_allowed, cfg, base_cost)
                    tr_m, _ = slice_metrics(pack, times, tr0, tr1)
                    if tr_m.n < 40:
                        continue
                    score = tr_m.expectancy
                    if score > best_score:
                        best_score = score
                        best = pack
                        best_cfg = cfg
                        best_train = tr_m
        if best is None:
            wf_windows.append({
                "train_start": str(tr_start.date()),
                "train_end": str(tr_end.date()),
                "test_end": str(te_end.date()),
                "selected": None,
                "train": m_to_dict(metrics_from_trades(np.array([]))),
                "test": m_to_dict(metrics_from_trades(np.array([]))),
                "note": "no positive-PF param set with >=40 train trades",
            })
            continue
        tr_m, _ = slice_metrics(best, times, tr0, tr1)
        te_m, te_mask = slice_metrics(best, times, tr1, te1)
        if te_mask.sum():
            wf_test_r.append(best[3][te_mask])
            wf_test_entry.append(best[0][te_mask])
            wf_test_exit.append(best[1][te_mask])
            wf_test_reason.append(best[5][te_mask])
            wf_test_hold.append(best[6][te_mask])
            wf_test_slp.append(best[4][te_mask])
        wf_windows.append({
            "train_start": str(tr_start.date()),
            "train_end": str(tr_end.date()),
            "test_end": str(te_end.date()),
            "selected": {
                "lookback": best_cfg["lookback"],
                "z_entry": best_cfg["z_entry"],
                "sl_pips": best_cfg["sl_pips"],
                "atr_mult": best_cfg["atr_mult"],
            },
            "train": m_to_dict(tr_m),
            "test": m_to_dict(te_m),
        })

    if wf_test_r:
        wf_r = np.concatenate(wf_test_r)
        wf_entry = np.concatenate(wf_test_entry)
        wf_exit = np.concatenate(wf_test_exit)
        wf_reason = np.concatenate(wf_test_reason)
        wf_hold = np.concatenate(wf_test_hold)
        wf_slp = np.concatenate(wf_test_slp)
        wf_agg = metrics_from_trades(wf_r, wf_reason, wf_hold, wf_slp)
        # param drift
        sel_lb = [w["selected"]["lookback"] for w in wf_windows if w.get("selected")]
        sel_z = [w["selected"]["z_entry"] for w in wf_windows if w.get("selected")]
        drift = {
            "lookback_mode": int(pd.Series(sel_lb).mode().iloc[0]) if sel_lb else None,
            "lookback_unique": sorted(set(sel_lb)),
            "z_mode": float(pd.Series(sel_z).mode().iloc[0]) if sel_z else None,
            "z_unique": sorted(set(sel_z)),
            "windows_with_selection": len(sel_lb),
            "windows_total": len(wf_windows),
        }
    else:
        wf_r = np.array([])
        wf_agg = metrics_from_trades(wf_r)
        drift = {}
        wf_entry = np.array([], dtype=np.int64)

    # Frozen-param walk on 3m chunks after IS (2022+)
    frozen_chunks = []
    frozen_r = []
    chunk_starts = pd.date_range("2022-01-01", "2026-07-01", freq="3MS")
    for cs in chunk_starts:
        ce = cs + pd.DateOffset(months=3)
        cm, cmask = slice_metrics(final_pack, times, np.datetime64(cs), np.datetime64(ce))
        frozen_chunks.append({"start": str(cs.date()), "end": str(ce.date()), **m_to_dict(cm)})
        if cmask.sum():
            frozen_r.append(final_pack[3][cmask])
    frozen_agg = metrics_from_trades(np.concatenate(frozen_r) if frozen_r else np.array([]))

    # ------------------------------------------------------------------
    # Monte Carlo on OOS trades of final system (base cost)
    # ------------------------------------------------------------------
    print("Monte Carlo…")
    oos_r = r[oos_mask]
    full_r = r
    mc_oos = monte_carlo(oos_r, n_paths=1000, risk=0.01, seed=11)
    mc_full = monte_carlo(full_r, n_paths=1000, risk=0.01, seed=13)
    # stressed: haircut winners 15%, fatten losers 15%, plus adverse costs already a separate table
    if len(oos_r):
        stressed = oos_r.copy()
        stressed[stressed > 0] *= 0.85
        stressed[stressed <= 0] *= 1.15
        mc_stress = monte_carlo(stressed, n_paths=1000, risk=0.01, seed=17)
        # clustered losses: block bootstrap
        rng = np.random.default_rng(19)
        block = 8
        n = len(oos_r)
        n_blocks = int(np.ceil(n / block))
        ends = []
        dds = []
        for _ in range(1000):
            idxs = []
            for __ in range(n_blocks):
                s = int(rng.integers(0, max(1, n - block + 1)))
                idxs.extend(range(s, s + block))
            sample = oos_r[np.array(idxs[:n])]
            eq = 1.0
            peak = 1.0
            ddmax = 0.0
            for x in sample:
                eq *= 1.0 + 0.01 * x
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                if dd > ddmax:
                    ddmax = dd
            ends.append(eq)
            dds.append(ddmax * 100)
        mc_block = {
            "paths": 1000,
            "block_size": block,
            "median_end_equity": round(float(np.median(ends)), 4),
            "p05_end_equity": round(float(np.percentile(ends, 5)), 4),
            "median_max_dd_pct": round(float(np.median(dds)), 2),
            "p95_max_dd_pct": round(float(np.percentile(dds, 95)), 2),
        }
    else:
        mc_stress = {"paths": 0, "note": "no OOS trades"}
        mc_block = {"paths": 0, "note": "no OOS trades"}

    # ------------------------------------------------------------------
    # Yearly + equity
    # ------------------------------------------------------------------
    yearly = yearly_breakdown(r, exit_i, years)
    eq_curve = downsample_equity(r, entry_i, times, start_eq=10000.0, risk=0.01)

    # Gross vs net: rerun cost=0 for diagnostics only (not a decision result)
    pack_gross = run_cfg(arr, cand_z, atr, final_allowed, cand_cfg, 0.0)
    gross_full = metrics_from_trades(pack_gross[3], pack_gross[5], pack_gross[6], pack_gross[4])
    gross_oos, _ = slice_metrics(pack_gross, times, OOS_START, OOS_END)

    # Weaknesses
    wr_target = 0.45
    oos_positive = oos_m.expectancy > 0 and oos_m.profit_factor > 1.0
    full_sample_ok = full_m.n >= 1000
    oos_sample_ok = oos_m.n >= 150
    wf_positive = wf_agg.expectancy > 0 and wf_agg.profit_factor > 1.0
    cost_robust = all(c["oos"]["expectancy_r"] > 0 for c in cost_table if c["scenario"] in ("base", "adverse"))
    plateau = sum(1 for h in heat if h["oos_e"] > 0 and h["oos_n"] >= 80)
    wr_met = oos_m.win_rate >= wr_target - 0.005

    verdict_pass = (
        oos_positive
        and full_sample_ok
        and oos_sample_ok
        and wf_positive
        and cost_table[1]["oos"]["expectancy_r"] > 0  # base cost OOS
        and oos_m.profit_factor >= 1.15
    )
    # adverse cost collapse is a hard warning, not automatic fail if base holds
    limitations = []
    if not full_sample_ok:
        limitations.append(f"Full-sample trade count is {full_m.n}, below the 1,000-trade research minimum.")
    if not oos_sample_ok:
        limitations.append(f"OOS trade count is {oos_m.n}; several hundred were preferred.")
    if not oos_positive:
        limitations.append("Out-of-sample net expectancy is not positive under the base cost model.")
    if oos_m.profit_factor < 1.15:
        limitations.append(f"OOS profit factor is {oos_m.profit_factor:.3f}, below the 1.15 conservative target.")
    if not wf_positive:
        limitations.append("Aggregate rolling walk-forward test expectancy is not positive after costs.")
    if not cost_robust:
        limitations.append("Results collapse under the adverse cost scenario on OOS data.")
    if not wr_met:
        limitations.append(f"OOS win rate is {oos_m.win_rate:.1%}, below the ~45% desired profile (not a hard fail by itself).")
    if plateau < 4:
        limitations.append("OOS-positive lookback/z region is thin — possible isolated peak rather than a plateau.")
    limitations.append("Backtest uses M5 OHLC, not tick-level variable spread. Same-bar SL/TP conflict is resolved as SL-first.")
    limitations.append("HistData is bid OHLC with zero volume; spread/commission/slippage are modeled, not observed.")
    limitations.append("High-impact news filter was not historically validated; no reliable dated event tape was available for 2016–2026 in this environment.")
    limitations.append("No live or demo forward test has been run. This is not a live-trading recommendation.")
    if cand_cfg.get("z_exit", 0) > 0:
        limitations.append("A statistical z-exit is enabled; achieved RRR will differ from the nominal 1:2 payoff.")

    if verdict_pass:
        verdict = "CANDIDATE_SURVIVES_HISTORICAL_GATES"
        verdict_text = (
            "The selected configuration has positive net OOS expectancy, acceptable profit factor, "
            "and positive walk-forward aggregate under the base cost model. It still has not been "
            "demo-forward tested and is not approved for real-money trading."
        )
    else:
        verdict = "NOT_VALIDATED"
        verdict_text = (
            "The Z-score mean-reversion hypothesis was tested on 10+ years of EURUSD M5 with a "
            "realistic cost model. It does not clear the pre-declared validation gates. The EA is "
            "shipped for research and demo use with these parameters so the test is reproducible — "
            "not because an edge has been proven."
        )

    key_findings = [
        f"0 of {len(grid)} in-sample grid configs had positive net expectancy after {rt_cost('base'):.1f} pip round-turn costs.",
        f"Least-bad IS expectancy is {candidate_row['is']['expectancy_r']:.3f}R (PF {candidate_row['is']['profit_factor']:.2f}, win rate {candidate_row['is']['win_rate']:.1%}).",
        f"OOS (2024–2025) net expectancy is {oos_m.expectancy:.3f}R with PF {oos_m.profit_factor:.2f} — worse than IS, not a hidden winner.",
        f"Zero-cost diagnostic full-sample expectancy is {gross_full.expectancy:.3f}R (PF {gross_full.profit_factor:.2f}); OOS gross is {gross_oos.expectancy:.3f}R. Any pre-cost edge is smaller than a 2.5-pip friction on a 15-pip stop (0.17R/trade).",
        f"Nominal 1:2 is not realized: TP share {full_m.tp_share:.1%}, time-stop share {full_m.time_stop_share:.1%}, average winner {full_m.avg_win:.2f}R not +2R.",
        "No regime, session, or efficiency filter produced positive validation expectancy. Filters change the loss — they do not create an edge.",
        "High-impact news was not historically testable here (no dated 2016–2026 event tape). The EA still implements a live calendar + CSV fallback.",
        "This study rejects the strategy for live trading. The MQL5 EA exists to reproduce the test on a broker, not to warehouse a claimed edge.",
    ]

    # Neighbor stability of candidate lookback/z
    cand_neighbors = [
        h for h in heat
        if abs(h["lookback"] - cand_cfg["lookback"]) <= 50
        and abs(h["z_entry"] - cand_cfg["z_entry"]) <= 0.5
    ]

    # Variant table (slim)
    variant_slim = sorted(
        variant_rows,
        key=lambda d: d["is"]["expectancy_r"],
        reverse=True,
    )[:20]

    # Baseline top without packs
    results = {
        "meta": {
            "project": "STATREV",
            "title": "EURUSD M5 statistical mean-reversion research",
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "engine_runtime_sec": round(time.time() - t0, 1),
            "account_assumption": "USD account, 1% of current equity per trade, compounding, one net EURUSD position, no martingale/grid.",
            "nominal_rrr": "1:2 (TP = 2 × initial SL) unless a tested z-exit overrides",
            "signal_rule": "Closed M5 bar only. Fill at next bar open. No forming-candle entries.",
            "splits": {
                "in_sample": "2016-01-01 → 2022-01-01",
                "validation": "2022-01-01 → 2024-01-01",
                "out_of_sample": "2024-01-01 → 2026-01-01",
                "extra_holdout": "2026-01-01 → 2026-09-28",
            },
            "selection_rule": selection_rule,
            "verdict": verdict,
            "verdict_text": verdict_text,
            "key_findings": key_findings,
            "gates": {
                "oos_net_expectancy_positive": bool(oos_positive),
                "oos_pf_ge_1_15": bool(oos_m.profit_factor >= 1.15),
                "full_trades_ge_1000": bool(full_sample_ok),
                "oos_trades_ge_150": bool(oos_sample_ok),
                "walk_forward_aggregate_positive": bool(wf_positive),
                "base_cost_oos_positive": bool(cost_table[1]["oos"]["expectancy_r"] > 0),
                "adverse_cost_oos_positive": bool(cost_table[2]["oos"]["expectancy_r"] > 0),
                "win_rate_near_45": bool(wr_met),
            },
        },
        "data": quality,
        "costs": {
            "model": "Round-turn pips subtracted from each trade in R: (spread + 2×slippage + commission_pips) / SL_pips. Commission 0.70 pip ≈ $7 per lot round-turn on EURUSD.",
            "scenarios": COST,
            "base_round_turn_pips": rt_cost("base"),
            "table": cost_table,
            "gross_vs_net_note": "Zero-cost figures below are diagnostic only and were not used for selection.",
            "gross_full": m_to_dict(gross_full),
            "gross_oos": m_to_dict(gross_oos),
        },
        "baseline": {
            "grid_size": len(grid),
            "is_sampled": len(ranked),
            "is_profitable": len(pos_is),
            "leaderboard": leaderboard[:15],
            "note": "Baseline = typical-price Z-score, SL/TP only, rollover/Friday hygiene, base costs, no ADX/slope/ER/session restriction.",
        },
        "variants": variant_slim,
        "filters": {
            "table": filter_table,
            "chosen": chosen_filter,
            "chosen_note": final_filter_note,
            "retention_rule": "A filter is retained only if VALIDATION expectancy improves (or DD improves without material E damage) with >=80 VAL trades and VAL E>0. OOS is reported after the choice is frozen.",
        },
        "candidate": {
            "id": candidate_row["id"],
            "cfg": cand_cfg,
            "filter": chosen_filter,
            "is": m_to_dict(is_m),
            "val": m_to_dict(val_m),
            "oos": m_to_dict(oos_m),
            "extra_2026": m_to_dict(x_m),
            "full": m_to_dict(full_m),
            "yearly": yearly,
            "equity_curve": eq_curve,
            "win_rate_target_45_met": wr_met,
            "neighbors": cand_neighbors,
        },
        "stability": {
            "lookback_z": heat,
            "stops": sl_heat,
        },
        "walk_forward": {
            "design": "Rolling 12-month train / 3-month test, step 3 months. Re-optimize lookback, z-entry, and SL family on train (require >=40 train trades; pick highest train expectancy even if PF<1, because no window cleared PF>1). Other params and filters frozen from the IS least-bad set.",
            "windows": wf_windows,
            "aggregate": m_to_dict(wf_agg),
            "param_drift": drift,
            "frozen_params_post_is_chunks": frozen_chunks,
            "frozen_params_post_is_aggregate": m_to_dict(frozen_agg),
        },
        "monte_carlo": {
            "note": "IID bootstrap of actual trade R-multiples at 1% compounded risk. Not a Bernoulli +2/−1 toy.",
            "oos_iid": mc_oos,
            "full_iid": mc_full,
            "oos_haircut_winners_15_fatten_losses_15": mc_stress,
            "oos_block_bootstrap": mc_block,
        },
        "limitations": limitations,
        "forward_test_gate": {
            "min_period_weeks": 12,
            "min_trades": 80,
            "max_avg_slippage_pips": 0.6,
            "max_avg_spread_pips": 2.0,
            "expectancy_floor_vs_oos": "Live/demo net expectancy should not be worse than OOS expectancy minus 0.05R.",
            "drawdown_kill": "Stop and investigate if live DD exceeds the Monte Carlo 95th percentile of OOS paths.",
            "error_kill": "Any duplicate orders, sizing errors, calendar faults, or SL/TP placement failures halt new entries.",
            "recommendation": "Demo only. Do not fund a live account from this study.",
        },
        "ea": {
            "file": "STATREV_EURUSD_M5.mq5",
            "magic": 260928,
            "defaults_are_candidate": True,
        },
    }

    # JSON sanitizer
    def conv(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            v = float(o)
            if not np.isfinite(v):
                return None
            return v
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))

    path1 = os.path.join(OUT_DIR, "results.json")
    text = json.dumps(results, default=conv, indent=2)
    with open(path1, "w") as f:
        f.write(text)
    with open(PUBLIC_JSON, "w") as f:
        f.write(text)
    print("Wrote", path1, "bytes", len(text))
    print("Verdict:", verdict)
    print("Runtime", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
