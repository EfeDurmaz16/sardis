import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import Script from "next/script";
import { wedges, getWedgeBySlug } from "@/lib/wedge-data";
import { createBreadcrumbSchema } from "@/lib/metadata";

// Static generation for all wedge slugs
export function generateStaticParams() {
  return wedges.map((w) => ({ slug: w.slug }));
}

// Dynamic metadata per wedge
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const wedge = getWedgeBySlug(slug);
  if (!wedge) return {};

  return {
    title: wedge.metaTitle,
    description: wedge.description,
    alternates: {
      canonical: `https://www.sardis.sh/wedge/${wedge.slug}`,
    },
  };
}

export default async function WedgePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const wedge = getWedgeBySlug(slug);
  if (!wedge) notFound();

  const breadcrumbSchema = createBreadcrumbSchema([
    { name: "Home", href: "/" },
    { name: wedge.title },
  ]);

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      <Script
        id={`wedge-${wedge.slug}-breadcrumb`}
        type="application/ld+json"
        strategy="beforeInteractive"
      >
        {JSON.stringify(breadcrumbSchema)}
      </Script>

      {/* Hero */}
      <section className="pt-20 pb-16 md:pt-28 md:pb-24">
        <div className="max-w-4xl mx-auto px-5 text-center">
          <p
            className="text-xs font-semibold uppercase tracking-widest mb-4"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: "var(--landing-blue)",
            }}
          >
            {wedge.subtitle}
          </p>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-[-0.04em] mb-6"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              color: "var(--landing-text-primary)",
            }}
          >
            {wedge.heroTitle}
            <br />
            <span style={{ color: "var(--landing-accent)" }}>
              {wedge.heroHighlight}
            </span>
          </h1>
          <p
            className="text-base md:text-lg max-w-3xl mx-auto mb-10 font-light"
            style={{
              fontFamily: "'Inter', sans-serif",
              color: "var(--landing-text-tertiary)",
            }}
          >
            {wedge.heroDesc}
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href="https://dashboard.sardis.sh/signup"
              className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] inline-block hover:opacity-90"
              style={{
                fontFamily: "'Inter', sans-serif",
                backgroundColor: "var(--landing-accent)",
              }}
            >
              Get Started Free
            </a>
            <Link
              href="/docs"
              className="rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] inline-block hover:border-[var(--landing-text-muted)]"
              style={{
                fontFamily: "'Inter', sans-serif",
                border: "1px solid var(--landing-border)",
                color: "var(--landing-text-secondary)",
              }}
            >
              View Documentation
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="pb-20 md:pb-32">
        <div className="max-w-5xl mx-auto px-5">
          <div className="flex flex-col gap-4">
            {wedge.features.map((f, i) => (
              <div
                key={i}
                className="flex flex-col md:flex-row gap-6 md:gap-10 rounded-[14px] p-6 md:p-10"
                style={{
                  backgroundColor: "var(--landing-surface)",
                  border: "1px solid var(--landing-border)",
                }}
              >
                <div className="flex-1">
                  <span
                    className="text-[11px] uppercase tracking-wider font-medium px-2.5 py-0.5 rounded inline-block mb-4"
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      background: "rgba(59,130,246,0.1)",
                      color: "#3B82F6",
                      border: "1px solid rgba(59,130,246,0.15)",
                    }}
                  >
                    {f.tag}
                  </span>
                  <h2
                    className="font-semibold mb-3"
                    style={{
                      fontFamily: "'Space Grotesk', sans-serif",
                      fontSize: "24px",
                      lineHeight: "32px",
                      color: "var(--landing-text-primary)",
                    }}
                  >
                    {f.title}
                  </h2>
                  <p
                    className="text-[14px] font-light leading-[24px]"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      color: "var(--landing-text-tertiary)",
                    }}
                  >
                    {f.body}
                  </p>
                </div>
                <div className="md:w-[160px] md:shrink-0 flex md:flex-col items-center md:items-end justify-center">
                  <span
                    className="text-[28px] font-bold"
                    style={{
                      fontFamily: "'Space Grotesk', sans-serif",
                      color: "var(--landing-accent)",
                    }}
                  >
                    {f.stat}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-20 md:pb-32">
        <div className="max-w-3xl mx-auto px-5 text-center">
          <h2
            className="text-3xl md:text-4xl font-bold tracking-[-0.03em] mb-4"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              color: "var(--landing-text-primary)",
            }}
          >
            Give your agents a wallet.
          </h2>
          <p
            className="text-base mb-8 font-light"
            style={{
              fontFamily: "'Inter', sans-serif",
              color: "var(--landing-text-tertiary)",
            }}
          >
            Start building for free. No credit card required.
          </p>
          <a
            href="https://dashboard.sardis.sh/signup"
            className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] inline-block hover:opacity-90"
            style={{
              fontFamily: "'Inter', sans-serif",
              backgroundColor: "var(--landing-accent)",
            }}
          >
            Get Started Free
          </a>
        </div>
      </section>
    </div>
  );
}
