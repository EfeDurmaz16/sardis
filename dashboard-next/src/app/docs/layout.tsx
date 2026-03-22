"use client";
import DocsLayout from "@/components/docs/DocsLayout";
export default function DocsRouteLayout({ children }: { children: React.ReactNode }) {
  return <DocsLayout>{children}</DocsLayout>;
}
