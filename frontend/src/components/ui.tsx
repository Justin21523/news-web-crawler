import { clsx } from "clsx";
import { ArrowDownRight, ArrowRight, ArrowUpRight, CircleAlert } from "lucide-react";

type Tone = "primary" | "secondary" | "accent" | "success" | "warning" | "danger" | "info" | "neutral" | "magenta" | "green" | "yellow" | "blue";

const toneStyles: Record<Tone, { accent: string; soft: string; text: string; border: string }> = {
  primary: { accent: "bg-primary", soft: "bg-primary-soft-2", text: "text-primary-active", border: "border-primary/25" },
  secondary: { accent: "bg-secondary", soft: "bg-secondary-soft", text: "text-info-text", border: "border-info-border" },
  accent: { accent: "bg-accent", soft: "bg-accent-soft", text: "text-warn-text", border: "border-warn-border" },
  success: { accent: "bg-success", soft: "bg-success-soft", text: "text-success-text", border: "border-success-border" },
  warning: { accent: "bg-warn", soft: "bg-warn-soft", text: "text-warn-text", border: "border-warn-border" },
  danger: { accent: "bg-danger", soft: "bg-danger-soft", text: "text-danger-text", border: "border-danger-border" },
  info: { accent: "bg-info", soft: "bg-info-soft", text: "text-info-text", border: "border-info-border" },
  neutral: { accent: "bg-muted", soft: "bg-surface-muted", text: "text-text-secondary", border: "border-line" },
  magenta: { accent: "bg-[var(--module-ml)]", soft: "bg-[var(--module-ml-soft)]", text: "text-[var(--module-ml)]", border: "border-[color:var(--module-ml)]/25" },
  green: { accent: "bg-success", soft: "bg-success-soft", text: "text-success-text", border: "border-success-border" },
  yellow: { accent: "bg-accent", soft: "bg-accent-soft", text: "text-warn-text", border: "border-warn-border" },
  blue: { accent: "bg-secondary", soft: "bg-secondary-soft", text: "text-info-text", border: "border-info-border" },
};

export function Card({ children, className, tone = "neutral", ...props }: React.HTMLAttributes<HTMLElement> & { children: React.ReactNode; className?: string; tone?: Tone }) {
  return (
    <section
      {...props}
      className={clsx(
        "relative overflow-hidden rounded-lg border border-line bg-surface/95 p-5 shadow-card backdrop-blur",
        className,
      )}
    >
      <div className={clsx("absolute inset-x-0 top-0 h-1", toneStyles[tone].accent)} />
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  eyebrow,
  action,
  tone = "primary",
}: {
  title: string;
  eyebrow?: string;
  action?: React.ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        {eyebrow ? (
          <div className={clsx("inline-flex rounded-full border px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-wide", toneStyles[tone].soft, toneStyles[tone].text, toneStyles[tone].border)}>
            {eyebrow}
          </div>
        ) : null}
        <h2 className="mt-2 text-lg font-semibold text-ink">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function Button({
  children,
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { className?: string; variant?: "primary" | "secondary" | "ghost" | "export" | "danger" }) {
  const variants = {
    primary: "bg-primary text-white shadow-sm hover:bg-primary-hover active:bg-primary-active",
    secondary: "border border-line bg-surface-elevated text-ink hover:border-line-strong hover:bg-surface-muted",
    ghost: "text-muted hover:bg-surface-muted hover:text-ink",
    export: "bg-secondary text-white shadow-sm hover:bg-info-text",
    danger: "bg-danger text-white shadow-sm hover:bg-danger-text",
  };
  return (
    <button
      className={clsx(
        "focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={clsx("focus-ring h-10 w-full rounded-md border border-line bg-surface-elevated px-3 text-sm text-ink shadow-[var(--shadow-inset)] transition placeholder:text-muted hover:border-line-strong", className)}
      {...props}
    />
  );
}

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={clsx("focus-ring h-10 w-full rounded-md border border-line bg-surface-elevated px-3 text-sm text-ink shadow-[var(--shadow-inset)] transition hover:border-line-strong", className)}
      {...props}
    />
  );
}

export function StatusBadge({ status }: { status?: string | null }) {
  const tone =
    status === "succeeded" || status === "ready" || status === "complete"
      ? "border-success-border bg-success-soft text-success-text"
      : status === "failed" || status === "abandoned" || status === "danger" || status === "error"
        ? "border-danger-border bg-danger-soft text-danger-text"
        : status === "running"
          ? "border-info-border bg-info-soft text-info-text"
          : status === "warning"
            ? "border-warn-border bg-warn-soft text-warn-text"
            : "border-line bg-surface-muted text-text-secondary";
  return <span className={clsx("rounded-full border px-2.5 py-1 text-xs font-semibold", tone)}>{status || "unknown"}</span>;
}

export function KpiCard({
  label,
  value,
  detail,
  trend = "flat",
  tone = "primary",
}: {
  label: string;
  value: string | number;
  detail?: string;
  trend?: "up" | "down" | "flat";
  tone?: Tone;
}) {
  const TrendIcon = trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : ArrowRight;
  const styles = toneStyles[tone];
  return (
    <Card tone={tone}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-medium text-muted">{label}</div>
          <div className="numeric mt-2 text-3xl font-semibold text-ink">{value}</div>
          {detail ? <div className="mt-2 text-sm leading-5 text-text-secondary">{detail}</div> : null}
        </div>
        <div className={clsx("rounded-md border p-2", styles.soft, styles.text, styles.border)}>
          <TrendIcon className="h-5 w-5" />
        </div>
      </div>
    </Card>
  );
}

export function ChartNote({ children }: { children: React.ReactNode }) {
  return <p className="mt-4 border-t border-line pt-3 text-xs leading-5 text-muted">{children}</p>;
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-surface-elevated/80 p-8 text-center shadow-[var(--shadow-inset)]">
      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-md border border-info-border bg-info-soft text-info-text">
        <CircleAlert className="h-5 w-5" />
      </div>
      <div className="font-semibold text-ink">{title}</div>
      {detail ? <div className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">{detail}</div> : null}
    </div>
  );
}
