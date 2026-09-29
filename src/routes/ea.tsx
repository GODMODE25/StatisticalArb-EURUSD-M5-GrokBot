import { createFileRoute } from "@tanstack/react-router";
import { Card, CardHeader } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { research } from "@/lib/research";
import { formulas } from "@/lib/research";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/ea")({ component: EAPage });

function EAPage() {
  const cfg = research.candidate.cfg;
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-subtle">Deliverable</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">MQL5 Expert Advisor</h1>
        <p className="mt-3 text-muted">
          Compilable, modular, no DLLs. Defaults are the least-bad researched set. The source header states
          the rejection in plain language so a future you cannot “forget” the study.
        </p>
      </header>

      <Card>
        <CardHeader title="Download" kicker={research.ea.file} />
        <div className="flex flex-wrap gap-3">
          <a href="/ea/STATREV_EURUSD_M5.mq5" download className={cn(buttonVariants())}>
            STATREV_EURUSD_M5.mq5
          </a>
          <a href="/ea/README.txt" download className={cn(buttonVariants({ variant: "secondary" }))}>
            Setup notes
          </a>
          <a href="/ea/STATREV_news.csv" download className={cn(buttonVariants({ variant: "secondary" }))}>
            News CSV template
          </a>
          <a href="/research/results.json" download className={cn(buttonVariants({ variant: "ghost" }))}>
            results.json
          </a>
        </div>
        <p className="mt-4 text-sm text-muted">
          Copy the .mq5 into <span className="font-mono text-fg">MQL5/Experts/</span>, compile with F7, attach
          to EURUSD M5. Demo or Strategy Tester only.
        </p>
      </Card>

      <Card>
        <CardHeader title="Architecture" kicker="One file, explicit modules" />
        <ul className="grid gap-2 text-sm text-muted sm:grid-cols-2">
          {[
            "Controller — new M5 bar, magic isolation, kill switch",
            "Z-score — sample std, typical/close/residual, closed bar only",
            "Regime — ADX, ATR-normalized H1 slope, vol ratio, Kaufman ER",
            "News — CalendarValueHistory + CSV fallback, cached",
            "Session — rollover and Friday-late blocks, optional window",
            "Risk — 1% of current equity via tick size / tick value",
            "Execution — CTrade, broker SL/TP, filling by symbol",
            "Management — time stop, optional z-exit, cooldown, one position",
            "Logging — z, spread, lot, SL/TP, retcodes, reject reasons",
            "Panel — on-chart status including next news and DD",
          ].map((x) => (
            <li key={x} className="rounded-lg bg-elevated px-3 py-2 text-fg">
              {x}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <CardHeader title="Default inputs (match the study)" />
        <dl className="grid grid-cols-2 gap-2 font-mono text-sm sm:grid-cols-3">
          {[
            ["InpMode", "DEMO (use RESEARCH in tester)"],
            ["InpLookback", String(cfg.lookback)],
            ["InpZEntry", String(cfg.z_entry)],
            ["InpPriceMode", "Typical"],
            ["InpSLPips", String(cfg.sl_pips)],
            ["InpTPRR", String(cfg.tp_rr)],
            ["InpMaxHoldBars", String(cfg.max_hold)],
            ["InpCooldownBars", String(cfg.cooldown)],
            ["InpRiskPercent", "1.0"],
            ["InpMagic", String(research.ea.magic)],
            ["Regime filters", "all false"],
            ["InpUseNewsFilter", "false (untested historically)"],
          ].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-elevated px-3 py-2">
              <dt className="text-xs text-subtle">{k}</dt>
              <dd className="text-fg">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card>
        <CardHeader title="Position sizing" kicker={formulas.lots} />
        <p className="text-sm leading-relaxed text-muted">
          Risk money is a fraction of <em>current equity</em>, not balance, not a fixed lot. Distance is
          measured in ticks from the actual stop. Volume is snapped to the broker’s min / max / step and
          reduced if free margin cannot support it. There is no pip-value hardcode, no 5-digit assumption
          beyond detecting 3/5-digit pip size for the <em>input</em> of “15 pips.”
        </p>
        <p className="mt-3 text-sm text-muted">
          Forbidden on purpose: martingale, grid, averaging into a loss, recovery sizing, hedging the other
          side. One net EURUSD strategy position per magic number.
        </p>
      </Card>

      <Card>
        <CardHeader title="Modes" />
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-elevated p-4">
            <h3 className="font-medium">RESEARCH</h3>
            <p className="mt-2 text-sm text-muted">
              Closest match to the Python engine. Use this in Strategy Tester when you want to compare
              broker data to the HistData study. News off unless you supply a CSV.
            </p>
          </div>
          <div className="rounded-lg bg-elevated p-4">
            <h3 className="font-medium">DEMO</h3>
            <p className="mt-2 text-sm text-muted">
              Same signal. Daily loss, max drawdown kill, consecutive-loss pause, max trades/day. Still not
              a live-trading recommendation — it is a paper-trading harness with brakes.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
