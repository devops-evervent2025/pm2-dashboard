import type { Metadata } from "next";
import "./globals.css";

import { AuthProvider } from "@/lib/auth";
import AOSProvider from "@/components/AOSProvider";

export const metadata: Metadata = {
  title: "PM2 Dashboard",
  description: "Centralized PM2 process monitoring across clients and servers",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AOSProvider>
          <AuthProvider>{children}</AuthProvider>
        </AOSProvider>
      </body>
    </html>
  );
}
