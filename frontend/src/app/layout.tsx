import type { Metadata } from "next";

import { QueryProvider } from "@/components/query-provider";
import { Shell } from "@/components/shell";
import { I18nProvider } from "@/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "News Crawler Console",
  description: "Dashboard for the news crawler and analysis pipeline",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>
        <QueryProvider>
          <I18nProvider>
            <Shell>{children}</Shell>
          </I18nProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
