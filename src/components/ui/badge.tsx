import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "neutral",
  children,
}: {
  className?: string;
  tone?: "neutral" | "good" | "bad" | "warn";
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium tracking-wide",
        tone === "neutral" && "bg-elevated text-muted",
        tone === "good" && "bg-positive/15 text-positive",
        tone === "bad" && "bg-negative/15 text-negative",
        tone === "warn" && "bg-warn/15 text-warn",
        className,
      )}
    >
      {children}
    </span>
  );
}
