STATREV EURUSD M5 — Expert Advisor
==================================

RESEARCH STATUS: NOT VALIDATED FOR LIVE TRADING.

A 10.7-year HistData EURUSD M5 study (2016-01-03 to 2026-09-24, 791,666
M5 bars, 600-config grid, IS/VAL/OOS, walk-forward, Monte Carlo) found
zero in-sample configurations with positive net expectancy after 2.5 pip
round-turn costs. This EA reproduces the least-bad researched parameter
set so you can run it in MetaTrader 5 Strategy Tester and on a demo
account. It is not a recommendation to trade live.

Install
-------
1. Copy STATREV_EURUSD_M5.mq5 into:
   [Data Folder]/MQL5/Experts/
2. Optional: copy STATREV_news.csv into:
   [Data Folder]/MQL5/Files/
   (tester CSV fallback when the economic calendar is empty)
3. Compile in MetaEditor (F7). There are no DLL dependencies.
4. Attach to EURUSD, timeframe M5.

Defaults (least-bad historical set)
-----------------------------------
  Price           Typical (H+L+C)/3
  Lookback        75
  Z entry         3.0
  Confirm         Immediate
  SL              15.0 pips (fixed)
  TP              2 × SL  (30 pips)
  Max hold        48 M5 bars
  Cooldown        6 M5 bars
  Z-exit          off
  Risk            1% of current equity
  Magic           260928
  Regime filters  all OFF (none produced positive validation expectancy)
  News filter     OFF historically (no dated tape in the study); enable
                  for demo if you want live-calendar blackouts

Modes
-----
  RESEARCH  Closest match to the Python engine. Use in Strategy Tester.
  DEMO      Same signal, plus daily-loss / max-DD / consecutive-loss
            pauses. Still not a live go-ahead.

Strategy Tester (reproduce the study)
-------------------------------------
  Symbol          EURUSD
  Timeframe       M5
  Dates           2016.01.01 – 2026.09.24 (or your broker's history)
  Model           Every tick based on real ticks if available;
                  otherwise 1-minute OHLC. The study itself used M5
                  OHLC with conservative SL-before-TP, so tester tick
                  results will differ.
  Deposit         10,000 USD (or any; sizing is percent-of-equity)
  Leverage        1:100 or your demo
  Optimization    Do not hunt a profitable peak. The 600-config grid
                  already showed no positive-E plateau after costs.

Commission / spread in tester
-----------------------------
Model 2.5 pips round-turn as the base case:
  spread 1.2 pips + slippage 0.3 each way + commission 0.7 pip
  (~$7 per lot round-turn on EURUSD).

If your tester uses a custom commission, set it to match and keep
InpMaxSpreadPips = 2.0.

News CSV format (MQL5/Files/STATREV_news.csv)
---------------------------------------------
  2024.01.12 13:30,USD,high,Non-Farm Payrolls
  2024.01.25 13:30,USD,high,Core PCE

Forward / demo gate (declared in advance)
-----------------------------------------
Do not interpret a lucky week as validation.
  Minimum 12 weeks and 80 trades
  Average spread <= 2.0 pips, slippage <= 0.6 pips
  Net expectancy not worse than OOS (-0.18R) minus 0.05R
  Stop if live DD exceeds the OOS Monte Carlo 95th percentile (~88%)
  Halt on duplicate orders, sizing errors, or SL/TP placement failures

The OOS Monte Carlo at 1% risk already implies ~100% probability of a
20%+ drawdown. That is a hard operational warning, not a tuning target.
