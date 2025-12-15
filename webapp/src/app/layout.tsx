import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Copper CRM",
  description: "Login and import CSVs",
  icons: [{ rel: "icon", url: "/copper.png" }],
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
