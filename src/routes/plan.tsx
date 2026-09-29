import { createFileRoute } from "@tanstack/react-router";
import { Card, CardHeader } from "@/components/ui/card";
import { formulas, research } from "@/lib/research";

export const Route = createFileRoute("/plan")({ component: Plan });

function Plan() {
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Stage 0</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">Research plan</h1>
        <p className="mt-3 text-muted">
          Written before looking at a leaderboard. The goal was to test a single-asset statistical
          mean-reversion hypothesis on EURUSD M5 — not to produce a profitable-looking backtest.
        </p>
      </header>

      <Card>
        <CardHeader title="Hypothesis" kicker="What had to be true" />
        <p className="text-sm leading-relaxed text-muted sm:text-base">
          Closed-bar Z-score extremes of EURUSD revert often enough that a predefined −1R stop and +2R
          target has positive expectancy after spread, commission, and slippage. One position at a time,
          1% of current equity, no martingale or grid. Mean reversion, not trend following.
        </p>
        <dl className="mt-5 grid gap-3 font-mono text-sm sm:grid-cols-2">
          {Object.entries(formulas).map(([k, v]) => (
            <div key={k} className="rounded-lg bg-elevated px-3 py-2">
              <dt className="text-xs uppercase tracking-wider text-subtle">{k}</dt>
              <dd className="mt-1 text-fg">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card>
        <CardHeader title="Splits" kicker="Chronological, no shuffling" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-subtle">
              <tr>
                <th className="pb-2 font-medium">Role</th>
                <th className="pb-2 font-medium">Window</th>
                <th className="pb-2 font-medium">Used for</th>
              </tr>
            </thead>
            <tbody className="text-fg">
              <tr className="border-t border-border">
                <td className="py-2">In-sample</td>
                <td className="py-2 font-mono">{research.meta.splits.in_sample}</td>
                <td className="py-2 text-muted">Grid search, least-bad selection</td>
              </tr>
              <tr className="border-t border-border">
                <td className="py-2">Validation</td>
                <td className="py-2 font-mono">{research.meta.splits.validation}</td>
                <td className="py-2 text-muted">Filter retention (not OOS)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="py-2">Out-of-sample</td>
                <td className="py-2 font-mono">{research.meta.splits.out_of_sample}</td>
                <td className="py-2 text-muted">Unseen. Never used to pick params</td>
              </tr>
              <tr className="border-t border-border">
                <td className="py-2">Extra holdout</td>
                <td className="py-2 font-mono">{research.meta.splits.extra_holdout}</td>
                <td className="py-2 text-muted">2026 YTD, also unseen</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-sm text-muted">{research.meta.selection_rule}</p>
      </Card>

      <Card>
        <CardHeader title="Assumptions vs facts" kicker="Keep these apart" />
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-medium text-fg">Facts</h3>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted">
              <li>HistData ASCII EURUSD M1 bid OHLC, resampled to M5.</li>
              <li>791,666 M5 bars, 2016-01-03 17:00 to 2026-09-24 19:55 (Eastern wall clock).</li>
              <li>Closed-bar signals; fill at next bar open; SL-before-TP if both in range.</li>
              <li>{"600-config baseline grid; 0 configs with IS net E > 0 after 2.5 pip costs."}</li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-medium text-fg">Assumptions</h3>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted">
              <li>Round-turn cost modeled, not observed tick spread.</li>
              <li>Timestamps treated as HistData Eastern wall time (no DST correction).</li>
              <li>Commission 0.70 pip ≈ $7 / lot RT on a USD account.</li>
              <li>News filter could not be historically validated (no dated event tape).</li>
            </ul>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="What would have counted as a candidate" kicker="Gates, declared up front" />
        <ul className="space-y-2 text-sm text-muted">
          <li>{"Net OOS expectancy > 0 and PF ≳ 1.15 after base costs."}</li>
          <li>≥ 1,000 trades on the full tape; several hundred in OOS if possible.</li>
          <li>Walk-forward aggregate still positive; parameter plateau, not a spike.</li>
          <li>Does not collapse under adverse costs; Monte Carlo DD at 1% risk acceptable.</li>
          <li>Win rate near 45% was desired, not forced if expectancy was better another way.</li>
        </ul>
        <p className="mt-4 text-sm text-fg">
          The study did not clear those gates. The EA is still published so the test can be reproduced.
        </p>
      </Card>
    </div>
  );
}
