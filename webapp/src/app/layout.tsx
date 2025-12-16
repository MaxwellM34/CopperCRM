import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Copper CRM",
  description: "Login and import CSVs",
  icons: [
    { rel: "icon", url: "/copper.png", sizes: "32x32" },
    { rel: "icon", url: "/copper.png", sizes: "64x64" },
    { rel: "icon", url: "/copper.png", sizes: "128x128" },
    { rel: "icon", url: "/copper.png", sizes: "192x192" },
    { rel: "apple-touch-icon", url: "/copper.png", sizes: "192x192" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
