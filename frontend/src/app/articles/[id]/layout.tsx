import type { ReactNode } from "react";

export function generateStaticParams() {
  return [{ id: "demo-article-001" }];
}

export default function ArticleDetailLayout({ children }: { children: ReactNode }) {
  return children;
}
