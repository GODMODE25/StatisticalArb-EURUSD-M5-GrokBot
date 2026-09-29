import raw from "@/data/research.json";

export type Metrics = {
  trades: number;
  win_rate: number;
  expectancy_r: number;
  avg_win_r: number;
  avg_loss_r: number;
  payoff: number;
  profit_factor: number;
  sum_r: number;
  max_dd_r: number;
  max_dd_pct_1pct_risk: number;
  end_equity_multiple: number;
  time_stop_share: number;
  sl_share: number;
  tp_share: number;
  z_exit_share: number;
  avg_hold_bars: number;
  avg_sl_pips: number;
  median_r: number;
  p05_r: number;
  p95_r: number;
  year?: number;
};

export type Cfg = {
  price: string;
  lookback: number;
  z_entry: number;
  confirm: number;
  persist_n: number;
  sl_pips: number;
  atr_mult: number;
  tp_rr: number;
  max_hold: number;
  cooldown: number;
  z_exit: number;
};

export type Research = {
  meta: {
    project: string;
    title: string;
    generated_at: string;
    engine_runtime_sec: number;
    account_assumption: string;
    nominal_rrr: string;
    signal_rule: string;
    splits: Record<string, string>;
    selection_rule: string;
    verdict: string;
    verdict_text: string;
    key_findings: string[];
    gates: Record<string, boolean>;
  };
  data: {
    source: string;
    timestamp_convention: string;
    m1_bars: number;
    m5_bars: number;
    start: string;
    end: string;
    bars_by_year: Record<string, number>;
    gaps_note: string;
    spread_in_data: boolean;
    tick_model: string;
  };
  costs: {
    model: string;
    scenarios: Record<string, { spread: number; slip: number; comm: number; label: string }>;
    base_round_turn_pips: number;
    table: Array<{
      scenario: string;
      label: string;
      spread_pips: number;
      slippage_pips_one_way: number;
      commission_pips_rt: number;
      round_turn_pips: number;
      cost_in_r_vs_avg_sl: number | null;
      is: Metrics;
      val: Metrics;
      oos: Metrics;
      full: Metrics;
    }>;
    gross_vs_net_note: string;
    gross_full: Metrics;
    gross_oos: Metrics;
  };
  baseline: {
    grid_size: number;
    is_sampled: number;
    is_profitable: number;
    leaderboard: Array<{ id: string; cfg: Cfg; is: Metrics; val: Metrics; oos: Metrics; full: Metrics }>;
    note: string;
  };
  variants: Array<{ id: string; cfg: Cfg; is: Metrics; val: Metrics; oos: Metrics; full: Metrics }>;
  filters: {
    table: Array<{
      name: string;
      family: string;
      note: string;
      is: Metrics;
      val: Metrics;
      oos: Metrics;
      extra_2026: Metrics;
      full: Metrics;
      oos_delta_e: number;
      oos_delta_pf: number;
      oos_delta_dd: number;
      val_delta_e?: number;
      retained: boolean;
    }>;
    chosen: string;
    chosen_note: string;
    retention_rule: string;
  };
  candidate: {
    id: string;
    cfg: Cfg;
    filter: string;
    is: Metrics;
    val: Metrics;
    oos: Metrics;
    extra_2026: Metrics;
    full: Metrics;
    yearly: Metrics[];
    equity_curve: Array<{ t: string; equity: number; dd_pct: number; i: number }>;
    win_rate_target_45_met: boolean;
    neighbors: unknown[];
  };
  stability: {
    lookback_z: Array<{
      lookback: number;
      z_entry: number;
      is_e: number;
      is_pf: number;
      is_n: number;
      oos_e: number;
      oos_pf: number;
      oos_n: number;
    }>;
    stops: Array<{
      label: string;
      sl_pips: number;
      atr_mult: number;
      is: Metrics;
      oos: Metrics;
    }>;
  };
  walk_forward: {
    design: string;
    windows: Array<{
      train_start: string;
      train_end: string;
      test_end: string;
      selected: { lookback: number; z_entry: number; sl_pips: number; atr_mult: number } | null;
      train: Metrics;
      test: Metrics;
      note?: string;
    }>;
    aggregate: Metrics;
    param_drift: {
      lookback_mode?: number;
      lookback_unique: number[];
      z_mode?: number;
      z_unique: number[];
      windows_with_selection: number;
      windows_total: number;
    };
    frozen_params_post_is_chunks: unknown[];
    frozen_params_post_is_aggregate: Metrics;
  };
  monte_carlo: {
    note: string;
    oos_iid: Record<string, number | string>;
    full_iid: Record<string, number | string>;
    oos_haircut_winners_15_fatten_losses_15: Record<string, number | string>;
    oos_block_bootstrap: Record<string, number | string>;
  };
  limitations: string[];
  forward_test_gate: {
    min_period_weeks: number;
    min_trades: number;
    max_avg_slippage_pips: number;
    max_avg_spread_pips: number;
    expectancy_floor_vs_oos: string;
    drawdown_kill: string;
    error_kill: string;
    recommendation: string;
  };
  ea: { file: string; magic: number; defaults_are_candidate: boolean };
};

export const research = raw as unknown as Research;

export const splits = [
  { key: "is" as const, label: "In-sample", range: "2016–2021", hint: "Parameter selection" },
  { key: "val" as const, label: "Validation", range: "2022–2023", hint: "Filter / confirmation" },
  { key: "oos" as const, label: "Out-of-sample", range: "2024–2025", hint: "Unseen — not used to pick" },
  { key: "extra_2026" as const, label: "Holdout", range: "2026 YTD", hint: "Extra unseen" },
];

export function slLabel(cfg: Cfg) {
  if (cfg.atr_mult > 0) return `ATR×${cfg.atr_mult}`;
  return `${cfg.sl_pips} pips`;
}

export function confirmLabel(c: number) {
  return ["Immediate", "1-bar reversal", "Persistence", "Re-entry inside"][c] ?? String(c);
}

export function priceLabel(p: string) {
  if (p === "typical") return "Typical (H+L+C)/3";
  if (p === "close") return "Close";
  if (p === "residual") return "Close − EMA(50)";
  if (p === "atr_dev") return "(Close − mean) / ATR";
  return p;
}

export const formulas = {
  z: "Zₜ = (Pₜ − SMA(P, L)) / s(P, L)",
  pTypical: "Pₜ = (High + Low + Close) / 3",
  std: "s = sample standard deviation (n−1), closed bars only",
  lots: "lots = (equity × risk%) / ((SL / tickSize) × tickValue)",
  expectancy: "E[R] = (1/N) Σ Rᵢ",
  r: "R = side × (exit − entry) / SL_distance − cost_pips / SL_pips",
  cost: "cost_pips = spread + 2 × slippage + commission_pips",
  pf: "PF = Σ winners / |Σ losers|",
  compound: "equityₜ₊₁ = equityₜ × (1 + 0.01 × Rₜ)",
};
