export default function DocsDeployment() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">
            OPERATIONS
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Deployment Guide</h1>
        <p className="text-xl text-muted-foreground">
          Production-like staging deployment for Sardis API + landing demo live mode.
        </p>
      </div>

      <section className="not-prose mb-8 p-4 border border-emerald-500/30 bg-emerald-500/10">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
          <span className="font-bold text-emerald-500">STAGING LIVE</span>
        </div>
        <p className="text-sm text-muted-foreground">
          The public staging API and dashboard are live. SDKs are on{' '}
          <a href="https://pypi.org/user/sardis/" target="_blank" rel="noopener noreferrer" className="text-[var(--sardis-orange)] hover:underline">PyPI</a> and{' '}
          <a href="https://www.npmjs.com/org/sardis" target="_blank" rel="noopener noreferrer" className="text-[var(--sardis-orange)] hover:underline">npm</a>.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-xs font-mono">
          <a href="https://sardis-api-staging-ogq6bgc5rq-ue.a.run.app/health" target="_blank" rel="noopener noreferrer" className="px-2 py-1 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30 transition-colors">API Health</a>
          <a href="https://sardis-api-staging-ogq6bgc5rq-ue.a.run.app/api/v2/docs" target="_blank" rel="noopener noreferrer" className="px-2 py-1 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30 transition-colors">API Docs</a>
          <a href="https://app.sardis.sh" target="_blank" rel="noopener noreferrer" className="px-2 py-1 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30 transition-colors">Dashboard</a>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Recommended Architecture
        </h2>

        <div className="not-prose grid md:grid-cols-3 gap-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">Landing + Demo UI</h3>
            <p className="text-sm text-muted-foreground">
              Deploy on Vercel. Keep API keys server-side only and route live demo calls through
              <code className="px-1 py-0.5 bg-muted font-mono text-xs"> /api/demo-proxy</code>.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">Sardis API</h3>
            <p className="text-sm text-muted-foreground">
              Deploy containerized API on Cloud Run (recommended) or AWS App Runner.
              Use Postgres + Redis in staging.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">Data Layer</h3>
            <p className="text-sm text-muted-foreground">
              Neon Postgres + Upstash Redis is the fastest low-ops stack for design partner staging.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Required Environment Variables
        </h2>
        <p className="text-muted-foreground mb-4">
          Minimum variables for secure staging:
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# API
DATABASE_URL=postgresql://...
SARDIS_REDIS_URL=rediss://...
SARDIS_SECRET_KEY=...
JWT_SECRET_KEY=...
SARDIS_ADMIN_PASSWORD=...
SARDIS_STRICT_CONFIG=true

# Landing live demo (server-side only)
SARDIS_API_URL=https://<your-api-domain>
SARDIS_API_KEY=sk_...
DEMO_OPERATOR_PASSWORD=<shared-password>

# Optional live demo defaults
DEMO_LIVE_AGENT_ID=agent_demo_01
DEMO_LIVE_CARD_ID=card_demo_01`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Cloud Run (Recommended)
        </h2>
        <p className="text-muted-foreground mb-4">
          Use the built-in deploy script (includes build, deploy, health check, and post-deploy hints):
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# 1) Prepare local env file copy
cp deploy/gcp/staging/env.cloudrun.staging.yaml deploy/gcp/staging/env.cloudrun.staging.local.yaml

# 2) Generate strong secrets
bash ./scripts/generate_staging_secrets.sh --write deploy/env/.env.generated.secrets

# 3) Deploy
PROJECT_ID="<gcp-project-id>" \\
ENV_VARS_FILE="deploy/gcp/staging/env.cloudrun.staging.local.yaml" \\
bash ./scripts/deploy_gcp_cloudrun_staging.sh`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> AWS App Runner (Alternative)
        </h2>
        <p className="text-muted-foreground mb-4">
          If you prefer AWS credits/stack, use App Runner deployment automation:
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# 1) Prepare env
cp deploy/aws/staging/env.apprunner.staging.json deploy/aws/staging/env.apprunner.staging.local.json

# 2) Deploy
AWS_REGION="eu-central-1" \\
AWS_ACCOUNT_ID="<aws-account-id>" \\
ENV_JSON_FILE="deploy/aws/staging/env.apprunner.staging.local.json" \\
bash ./scripts/deploy_aws_apprunner_staging.sh`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Frontend Integration (Live Demo)
        </h2>
        <p className="text-muted-foreground mb-4">
          After API deploy, bootstrap API key and inject landing env vars in Vercel project settings.
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Bootstrap API key from deployed staging API
BASE_URL="https://<your-api-domain>" \\
ADMIN_PASSWORD="<SARDIS_ADMIN_PASSWORD>" \\
bash ./scripts/bootstrap_staging_api_key.sh

# Add these to Vercel (landing project):
SARDIS_API_URL=https://<your-api-domain>
SARDIS_API_KEY=<bootstrap-output>
DEMO_OPERATOR_PASSWORD=<shared-password>`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Verification
        </h2>
        <div className="not-prose grid md:grid-cols-3 gap-4">
          {[
            { name: 'API Health', path: '/health', desc: 'Must return 200 before live demo mode' },
            { name: 'Demo Auth', path: '/api/demo-auth', desc: 'Confirms operator lock + live config status' },
            { name: 'Demo Flow', path: '/demo', desc: 'Run blocked + approved scenarios end-to-end' },
          ].map((item) => (
            <div key={item.name} className="p-4 border border-border">
              <h3 className="font-bold font-display mb-1">{item.name}</h3>
              <code className="text-xs text-[var(--sardis-orange)] font-mono">{item.path}</code>
              <p className="text-sm text-muted-foreground mt-2">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Runbook References</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>
            → <code className="px-1 py-0.5 bg-muted font-mono text-xs">docs/release/api-deployment-plan-gcp-cloudrun.md</code>
          </li>
          <li>
            → <code className="px-1 py-0.5 bg-muted font-mono text-xs">docs/release/cloud-deployment-and-frontend-integration.md</code>
          </li>
          <li>
            → <code className="px-1 py-0.5 bg-muted font-mono text-xs">docs/release/investor-demo-operator-kit.md</code>
          </li>
        </ul>
      </section>
    </article>
  );
}
