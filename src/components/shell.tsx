import type { ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Verdict" },
  { to: "/plan", label: "Plan" },
  { to: "/data", label: "Data & costs" },
  { to: "/baseline", label: "Baseline" },
  { to: "/filters", label: "Filters" },
  { to: "/candidate", label: "Candidate" },
  { to: "/ea", label: "Expert Advisor" },
  { to: "/protocol", label: "Test protocol" },
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="min-h-dvh bg-bg text-fg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-fg"
      >
        Skip to content
      </a>
      <div className="mx-auto flex max-w-[1400px] flex-col lg:flex-row">
        <header className="border-b border-border lg:w-60 lg:shrink-0 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between gap-3 px-4 py-4 lg:block lg:px-5 lg:py-6">
            <Link to="/" className="block min-w-0">
              <p className="font-display text-2xl tracking-tight text-fg">STATREV</p>
              <p className="text-xs leading-snug text-muted">EURUSD M5 mean-reversion desk</p>
            </Link>
            <span className="rounded-full bg-negative/15 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-negative lg:mt-4 lg:inline-flex">
              Not validated
            </span>
          </div>
          <nav
            aria-label="Research sections"
            className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible lg:px-3 lg:pb-8"
          >
            {NAV.map((item) => {
              const active = pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "shrink-0 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150",
                    active ? "bg-elevated text-fg" : "text-muted hover:bg-elevated/60 hover:text-fg",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main id="main" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
