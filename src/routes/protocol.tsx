import { createFileRoute } from "@tanstack/react-router";
import { Card, CardHeader } from "@/components/ui/card";
import { research } from "@/lib/research";

export const Route = createFileRoute("/protocol")({ component: Protocol });

function Protocol() {
  const g = research.forward_test_gate;
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Reproduction</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">Test protocol</h1>
        <p className="mt-3 text-muted">{g.recommendation}</p>
      </header>

      <Card>
        <CardHeader title="MetaTrader 5 Strategy Tester" kicker="How to reproduce, not how to optimize a peak" />
        <dl className="space-y-3 text-sm">
          {[
            ["Symbol", "EURUSD (suffixes allowed; EA reads symbol properties)"],
            ["Timeframe", "M5"],
            ["Dates", "2016.01.01 – 2026.09.24, or as far as your broker history goes"],
            ["Model", "Every tick based on real ticks if you have them; otherwise 1-minute OHLC"],
            ["Spread", "Variable if possible. Else ~1.2 pips. Base study assumed 2.5 pip round-turn all-in"],
            ["Commission", "~$7 / lot round-turn (0.7 pip) for the base case"],
            ["Deposit", "10,000 USD (percent risk makes the starting capital a scale factor)"],
            ["Leverage", "Your demo, typically 1:100"],
            ["Forward in tester", "Do not use tester ‘forward’ to pick params — the study already split OOS"],
            ["Inputs", "Leave defaults, set InpMode = RESEARCH"],
            ["Optimization", "Do not. The 600-config grid is the search. Hunting a live peak is the failure mode."],
          ].map(([k, v]) => (
            <div key={k} className="grid gap-1 border-b border-border py-2 sm:grid-cols-[10rem_1fr]">
              <dt className="text-subtle">{k}</dt>
              <dd className="text-fg">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-sm text-muted">
          Broker M5 history is not HistData. Expect different trade counts. If a tester run is suddenly
          profitable, treat it as a data-mismatch investigation, not a discovery.
        </p>
      </Card>

      <Card>
        <CardHeader title="What the Python engine did" kicker={`Runtime ${research.meta.engine_runtime_sec}s`} />
        <ul className="list-disc space-y-1 pl-4 text-sm text-muted">
          <li>Resample M1 bid OHLC to M5; signal on closed bar; fill next open.</li>
          <li>Same-bar SL and TP conflict → SL first. Gap through SL → fill at open if worse.</li>
          <li>Round-turn pips converted to R and subtracted from every trade.</li>
          <li>H1 ADX and slope use the last <em>completed</em> H1 bar only (no intra-bar lookahead).</li>
          <li>Walk-forward re-fits lookback, Z, and SL family every 3 months on the prior 12 months.</li>
          <li>Monte Carlo bootstraps realized R-multiples — not a Bernoulli +2/−1 toy.</li>
        </ul>
      </Card>

      <Card>
        <CardHeader title="Demo / paper forward gate" kicker="Declared before any live decision" />
        <ul className="space-y-2 text-sm text-muted">
          <li>Minimum {g.min_period_weeks} weeks and {g.min_trades} trades.</li>
          <li>Average slippage ≤ {g.max_avg_slippage_pips} pips; average spread ≤ {g.max_avg_spread_pips} pips.</li>
          <li>{g.expectancy_floor_vs_oos}</li>
          <li>{g.drawdown_kill}</li>
          <li>{g.error_kill}</li>
        </ul>
        <p className="mt-4 text-sm text-fg">
          Given OOS Monte Carlo already implies near-certain 20%+ drawdown at 1% risk, a demo that “looks
          fine for two weeks” is not evidence. The prior is negative. The gate exists to stop, not to
          promote.
        </p>
      </Card>

      <Card>
        <CardHeader title="If you still want to iterate" />
        <p className="text-sm leading-relaxed text-muted">
          The study rejects <em>this</em> Z-score / 1:2 / M5 / EURUSD specification after realistic costs.
          It does not prove that every mean-reversion idea is dead. If you continue, change one thing at a
          time: a reachable take-profit (mean-reversion targets should be a fraction of an ATR, not 6×ATR),
          a cost-aware stop floor, or a different residual. Then rerun the same gates. Do not add indicators
          until a baseline without them has positive OOS expectancy.
        </p>
      </Card>
    </div>
  );
}
