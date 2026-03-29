import type { Metadata } from "next";
import localFont from "next/font/local";
import { Providers } from "./providers";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";

const geistSans = localFont({
  src: [
    { path: "../../public/fonts/geist/Geist-Regular.woff2", weight: "400" },
    { path: "../../public/fonts/geist/Geist-Medium.woff2", weight: "500" },
    { path: "../../public/fonts/geist/Geist-SemiBold.woff2", weight: "600" },
    { path: "../../public/fonts/geist/Geist-Bold.woff2", weight: "700" },
  ],
  variable: "--font-geist-sans",
  display: "swap",
});

const geistMono = localFont({
  src: [
    { path: "../../public/fonts/geist/GeistMono-Regular.woff2", weight: "400" },
    { path: "../../public/fonts/geist/GeistMono-Medium.woff2", weight: "500" },
    { path: "../../public/fonts/geist/GeistMono-Bold.woff2", weight: "700" },
  ],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sardis Dashboard",
  description: "Payment OS for the Agent Economy",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={cn(geistSans.variable, geistMono.variable, "font-sans")}>
      <body>
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  );
}
