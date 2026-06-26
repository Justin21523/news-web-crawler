import { clsx } from "clsx";
import { useEffect, useRef } from "react";
import { EmptyState } from "@/components/ui";

export type DisplayRow = Record<string, string | number | boolean | null | undefined>;

export function ScrollableTabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ key: T; label: string }>;
  active: T;
  onChange: (key: T) => void;
}) {
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const activeIndex = tabs.findIndex((tab) => tab.key === active);

  useEffect(() => {
    buttonRefs.current[activeIndex]?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [activeIndex]);

  return (
    <div className="tab-strip overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" role="tablist">
      <div className="flex min-w-max gap-1">
        {tabs.map((tab, index) => (
          <button
            key={tab.key}
            ref={(node) => { buttonRefs.current[index] = node; }}
            type="button"
            role="tab"
            id={`tab-${tab.key}`}
            aria-controls={`panel-${tab.key}`}
            aria-selected={active === tab.key}
            onClick={() => onChange(tab.key)}
            onKeyDown={(event) => {
              if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
              event.preventDefault();
              const nextIndex = event.key === "Home"
                ? 0
                : event.key === "End"
                  ? tabs.length - 1
                  : event.key === "ArrowRight"
                    ? (index + 1) % tabs.length
                    : (index - 1 + tabs.length) % tabs.length;
              onChange(tabs[nextIndex].key);
              buttonRefs.current[nextIndex]?.focus();
            }}
            className={clsx("tab-button", active === tab.key ? "tab-button-active" : "tab-button-inactive")}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function DataTable({
  title,
  rows,
  limit = 20,
  maxColumns = 8,
  emptyTitle = "No table data",
}: {
  title?: string;
  rows: DisplayRow[];
  limit?: number;
  maxColumns?: number;
  emptyTitle?: string;
}) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, maxColumns);
  return (
    <div>
      {title ? <div className="mb-3 text-sm font-semibold text-ink">{title}</div> : null}
      {rows.length ? (
        <div className="overflow-x-auto rounded-md border border-line bg-surface">
          <table className="min-w-[720px] divide-y divide-line text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-muted">
                {headers.map((header) => (
                  <th key={header} className="whitespace-nowrap px-3 py-2 font-semibold">
                    {header.replaceAll("_", " ")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.slice(0, limit).map((row, index) => (
                <tr key={index} className="transition hover:bg-primary-soft-2">
                  {headers.map((header) => (
                    <td key={header} className="max-w-[320px] truncate px-3 py-2 text-muted" title={String(row[header] ?? "")}>
                      {String(row[header] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title={emptyTitle} />
      )}
    </div>
  );
}

export function ChartFrame({
  children,
  empty,
  height = "h-72",
}: {
  children: React.ReactNode;
  empty?: boolean;
  height?: string;
}) {
  if (empty) {
    return <EmptyState title="No chart data" detail="Adjust filters or run the related analysis job." />;
  }
  return <div className={clsx("min-w-0", height)}>{children}</div>;
}

export function FilterChip({ label, onRemove }: { label: string; onRemove?: () => void }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary-soft-2 px-3 py-1 text-xs font-semibold text-primary-active">
      {label}
      {onRemove ? (
        <button type="button" onClick={onRemove} className="text-primary-active/70 hover:text-primary-active" aria-label={`Remove ${label}`}>
          x
        </button>
      ) : null}
    </span>
  );
}
