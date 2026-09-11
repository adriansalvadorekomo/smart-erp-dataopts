import { cn } from "@/lib/utils";
import type { DeliveryStatus } from "@/lib/api";

const DOT: Record<DeliveryStatus, string> = {
  "IN TRANSIT": "bg-[#0071e3]",
  DELIVERED: "bg-[#1d8127]",
  DELAYED: "bg-[#b25e09]",
  RETURNED: "bg-[#ff3b30]",
};

/** Quiet pill with a status dot — Apple-style, replaces the loud badge. */
export function StatusPill({ status, className }: { status: DeliveryStatus; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground",
        className
      )}
    >
      <span className={cn("size-1.5 rounded-full", DOT[status])} />
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </span>
  );
}
