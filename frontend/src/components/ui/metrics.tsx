/** Shared primitives used across every analytics page.
 * Each component has one job; nothing decorative lives here.
 */
import { cn } from "@/lib/utils";
import type { DeliveryStatus } from "@/lib/api";

// ─── Status pill (order lifecycle) ───────────────────────────────────────────

const STATUS_DOT: Record<DeliveryStatus, string> = {
  "IN TRANSIT": "bg-[#0071e3]",
  DELIVERED:   "bg-[#1d8127]",
  DELAYED:     "bg-[#b25e09]",
  RETURNED:    "bg-[#ff3b30]",
};

export function StatusPill({
  status,
  className,
}: {
  status: DeliveryStatus;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground",
        className
      )}
    >
      <span className={cn("size-1.5 shrink-0 rounded-full", STATUS_DOT[status])} />
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </span>
  );
}

// ─── KPI block ────────────────────────────────────────────────────────────────

export function Metric({
  label,
  value,
  sub,
  signal,
}: {
  label: string;
  value: string;
  sub?: string;
  /** "good" | "warn" | "bad" — colors the sub-label, not the value */
  signal?: "good" | "warn" | "bad";
}) {
  const sigClass =
    signal === "good"
      ? "text-[var(--success)]"
      : signal === "bad"
      ? "text-destructive"
      : signal === "warn"
      ? "text-[var(--warning)]"
      : "text-muted-foreground";
  return (
    <div>
      <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 text-[28px] font-semibold tracking-tight tabular-nums leading-none">
        {value}
      </p>
      {sub && (
        <p className={cn("mt-1 text-[13px] tabular-nums", sigClass)}>{sub}</p>
      )}
    </div>
  );
}

// ─── Inline bar (relative share within a list) ───────────────────────────────

export function InlineBar({
  share,
  className,
}: {
  share: number;
  className?: string;
}) {
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-secondary">
      <div
        className={cn("h-full rounded-full bg-primary", className)}
        style={{ width: `${Math.max(share * 100, 1)}%` }}
      />
    </div>
  );
}

// ─── Section header ───────────────────────────────────────────────────────────

export function SectionHeading({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div>
      <h1 className="text-[30px] font-semibold tracking-tight">{title}</h1>
      <p className="mt-1 text-[15px] text-muted-foreground">{description}</p>
    </div>
  );
}

// ─── Loading / error state ────────────────────────────────────────────────────

export function LoadingRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-6">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-4 animate-pulse rounded-full bg-secondary" />
      ))}
    </div>
  );
}
