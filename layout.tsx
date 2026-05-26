// src/app/layout.tsx
import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "react-hot-toast";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "GST Audit Pro — India's #1 GST Reconciliation Platform",
    template: "%s | GST Audit Pro",
  },
  description:
    "Auto-reconcile GSTR-1, GSTR-2B, GSTR-3B with your books. AI-powered mismatch detection for CAs and tax consultants.",
  keywords: ["GST audit", "GSTR reconciliation", "ITC matching", "GST compliance India", "CA software"],
  authors: [{ name: "GST Audit Pro" }],
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://gstauditpro.in",
    siteName: "GST Audit Pro",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.18.0/dist/tabler-icons.min.css"
        />
      </head>
      <body className={`${dmSans.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: "#1e293b",
              color: "#f1f5f9",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "13px",
              fontFamily: "var(--font-sans)",
            },
            success: { iconTheme: { primary: "#059669", secondary: "#ecfdf5" } },
            error:   { iconTheme: { primary: "#dc2626", secondary: "#fef2f2" } },
          }}
        />
      </body>
    </html>
  );
}
