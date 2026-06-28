import type { ReactNode } from "react";

export function generateStaticParams() {
  return [{ id: "demo-report-source-logistic" }];
}

export default function DiagnosticsReportDetailLayout({ children }: { children: ReactNode }) {
  return children;
}
