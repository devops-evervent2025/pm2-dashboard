import type { Metadata } from "next";
import "./globals.css";

import { AuthProvider } from "@/lib/auth";
import AOSProvider from "@/components/AOSProvider";
import { APP_NAME, getFaviconUrl } from "@/components/branding/config";

export const metadata: Metadata = {
  title: APP_NAME,
  description: "Centralized PM2 process monitoring across clients and servers",
  icons: {
    icon: getFaviconUrl(),
  },
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
