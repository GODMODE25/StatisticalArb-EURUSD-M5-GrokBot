import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section className={cn("rounded-xl bg-surface p-5 shadow-border sm:p-6", className)}>
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  kicker,
  action,
}: {
  title: string;
  kicker?: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        {kicker ? (
          <p className="mb-1 text-xs font-medium uppercase tracking-[0.14em] text-subtle">{kicker}</p>
        ) : null}
        <h2 className="font-display text-xl font-medium tracking-tight text-balance text-fg">{title}</h2>
      </div>
      {action}
    </header>
  );
}
