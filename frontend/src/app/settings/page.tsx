"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Server } from "lucide-react";

import { Card } from "@/components/ui";
import { API_BASE, api } from "@/lib/api";

export default function SettingsPage() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 15000 });

  return (
    <div className="page-shell">
      <div className="page-heading">
        <h1 className="text-2xl font-semibold text-ink">Settings</h1>
        <p className="mt-1 text-sm text-muted">Runtime paths and API health.</p>
      </div>

      <Card>
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-primary-soft p-3 text-primary-active">
            {health.data?.status === "ok" ? <CheckCircle2 className="h-5 w-5" /> : <Server className="h-5 w-5" />}
          </div>
          <div>
            <div className="font-semibold text-ink">API Status</div>
            <div className="text-sm text-muted">{health.data?.status || (health.isLoading ? "Checking" : "Unavailable")}</div>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold text-ink">Paths</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <Row label="Data directory" value={health.data?.data_dir || "Unknown"} />
          <Row label="SQLite database" value={health.data?.db_path || "Unknown"} />
          <Row label="Frontend API base" value={API_BASE} />
        </dl>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-2 border-b border-line pb-3 md:grid-cols-[180px_1fr]">
      <dt className="text-muted">{label}</dt>
      <dd className="break-all font-mono text-xs text-ink">{value}</dd>
    </div>
  );
}
